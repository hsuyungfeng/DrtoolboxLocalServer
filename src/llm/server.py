"""
LlamaCppServer - Local LLM inference server using llama.cpp.

This module provides a LlamaCppServer class for inference with Qwen 3.6 model
on NVIDIA 2080Ti GPU (22GB VRAM constraint).

Features:
- Model loading and management
- Synchronous and streaming generation
- Dynamic batching based on queue depth
- GPU memory monitoring and overflow prevention
- Request queue with timeout handling
"""

import os
import time
import queue
import threading
import logging
from typing import Optional, Generator, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, Future

# Try to import llama.cpp bindings
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
    print("[DEBUG] llama_cpp imported successfully")
except ImportError as e:
    print(f"[DEBUG] llama_cpp import failed: {e}")
    LLAMA_CPP_AVAILABLE = False
    Llama = None

# GPU memory monitoring
try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except Exception:
    NVML_AVAILABLE = False
    pynvml = None

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for text generation."""
    max_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    stream: bool = False
    stop: list = field(default_factory=lambda: ["</s>", "USER:"])
    
    def to_dict(self) -> dict:
        """Convert to llama.cpp kwargs."""
        return {
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
            "stop": self.stop,
        }


@dataclass
class GenerationResult:
    """Result of text generation."""
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    finish_reason: str = "stop"
    

class LlamaCppServer:
    """
    Local LLM inference server using llama.cpp.
    
    Manages model loading, inference requests, and GPU memory monitoring
    for Qwen 3.6 on NVIDIA 2080Ti GPU.
    
    Attributes:
        model_path: Path to quantized model file (Q8_0)
        model: Loaded Llama model instance
        config: Server configuration
    """
    
    def __init__(
        self,
        model_path: str,
        config_path: Optional[str] = None,
        n_ctx: int = 2048,
        n_threads: int = 4,
        n_gpu_layers: int = 0,
        kv_cache_quantization: bool = True,
    ):
        """
        Initialize llama.cpp server.
        
        Args:
            model_path: Path to GGUF model file (Q8_0 quantization)
            config_path: Optional path to config JSON
            n_ctx: Context window size
            n_threads: CPU threads for inference
            n_gpu_layers: GPU layers to offload (0 = all)
            kv_cache_quantization: Enable KV cache quantization
        """
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self.kv_cache_quantization = kv_cache_quantization
        
        self.model: Optional[Llama] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._request_queue: queue.Queue = queue.Queue()
        self._running = False
        self._batch_size = 1
        self._queue_depth = 0
        
        # GPU memory threshold (18GB for safety on 22GB card)
        self._vram_threshold = 18 * 1024 * 1024 * 1024  # 18GB
        
        # Memory monitoring config (loaded from memory_config.json)
        self._memory_config = self._load_memory_config()
        self._polling_interval = self._memory_config.get("polling_interval_seconds", 30)
        self._warning_threshold = self._memory_config.get("warning_threshold_gb", 18)
        self._critical_threshold = self._memory_config.get("critical_threshold_gb", 20)
        
        # Memory monitoring thread
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False
        
        # Load config if provided
        self.config = self._load_config(config_path) if config_path else {}
        
        logger.info(f"LlamaCppServer initialized: model={model_path}")
    
    def _load_memory_config(self) -> dict:
        """Load memory monitoring configuration."""
        import json
        default_config = {
            "polling_interval_seconds": 30,
            "warning_threshold_gb": 18,
            "critical_threshold_gb": 20,
            "alert_webhook": None,
        }
        
        try:
            with open("config/memory_config.json", "r") as f:
                user_config = json.load(f)
                return {**default_config, **user_config}
        except FileNotFoundError:
            return default_config
        except Exception as e:
            logger.warning(f"Failed to load memory config: {e}")
            return default_config
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        import json
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            return {}
    
    def load_model(self) -> bool:
        """
        Load the LLM model into memory.
        
        Returns:
            True if model loaded successfully
            
        Raises:
            RuntimeError: If model loading fails
        """
        if not LLAMA_CPP_AVAILABLE:
            raise RuntimeError("llama-cpp-python not installed")
        
        if not os.path.exists(self.model_path):
            raise RuntimeError(f"Model file not found: {self.model_path}")
        
        logger.info(f"Loading model from {self.model_path}...")
        start_time = time.time()
        
        try:
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                kv_cache_quantization=self.kv_cache_quantization,
                use_mmap=True,
                use_mlock=False,
                embedding=False,
                verbose=False,
            )
            
            elapsed = time.time() - start_time
            logger.info(f"Model loaded successfully in {elapsed:.2f}s")
            
            # Initialize thread pool for async inference
            self._executor = ThreadPoolExecutor(
                max_workers=self._batch_size + 2,
                thread_name_prefix="llama-inference"
            )
            self._running = True
            
            # Start GPU memory monitoring thread (D-10: every 30 seconds)
            self.start_memory_monitor()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Model loading failed: {e}")
    
    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """
        Generate text synchronously.
        
        Args:
            prompt: Input prompt/text
            config: Generation configuration
            
        Returns:
            GenerationResult with generated text and metadata
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        if config is None:
            config = GenerationConfig()
        
        start_time = time.time()
        
        try:
            output = self.model(
                prompt,
                **config.to_dict()
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract metrics
            prompt_tokens = output.get('evaluation_tokens', 0)
            completion_tokens = len(output.get('tokens', []))
            
            return GenerationResult(
                text=output.get('choices', [{}])[0].get('text', ''),
                model=os.path.basename(self.model_path),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=latency_ms,
                finish_reason=output.get('choices', [{}])[0].get('finish_reason', 'stop'),
            )
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    def streaming_generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> Generator[str, None, None]:
        """
        Generate text with streaming (token-by-token).
        
        Args:
            prompt: Input prompt/text
            config: Generation configuration
            
        Yields:
            Generated tokens as they're produced
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        if config is None:
            config = GenerationConfig()
        config.stream = True
        
        try:
            stream = self.model(prompt, **config.to_dict())
            
            for chunk in stream:
                if 'choices' in chunk and len(chunk['choices']) > 0:
                    token = chunk['choices'][0].get('delta', {}).get('content', '')
                    if token:
                        yield token
                        
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            raise
    
    def generate_async(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        timeout: float = 30.0,
    ) -> Future:
        """
        Submit generation request to async queue.
        
        Args:
            prompt: Input prompt/text
            config: Generation configuration
            timeout: Request timeout in seconds
            
        Returns:
            Future containing GenerationResult
        """
        if self._executor is None:
            raise RuntimeError("Model not loaded")
        
        self._queue_depth = self._request_queue.qsize()
        
        # Dynamic batching: increase batch size if queue is deep
        if self._queue_depth > 5:
            self._batch_size = min(4, self._batch_size + 1)
        elif self._queue_depth < 2:
            self._batch_size = max(1, self._batch_size - 1)
        
        # Check VRAM before accepting request
        if self._check_vram_overflow():
            logger.warning("VRAM threshold exceeded, rejecting request")
            raise RuntimeError("GPU memory overflow, try again later")
        
        # Submit to executor
        future = self._executor.submit(
            self._generate_with_timeout,
            prompt,
            config,
            timeout
        )
        
        return future
    
    def _generate_with_timeout(
        self,
        prompt: str,
        config: Optional[GenerationConfig],
        timeout: float,
    ) -> GenerationResult:
        """Generate with timeout handling."""
        try:
            return self.generate(prompt, config)
        except TimeoutError:
            logger.error(f"Generation timed out after {timeout}s")
            raise
    
    def _check_vram_overflow(self) -> bool:
        """Check if VRAM usage exceeds threshold."""
        if not NVML_AVAILABLE:
            return False
        
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            if memory_info.used > self._vram_threshold:
                logger.warning(
                    f"VRAM overflow: {memory_info.used / 1e9:.1f}GB used "
                    f"(threshold: {self._vram_threshold / 1e9:.1f}GB)"
                )
                return True
                
        except Exception as e:
            logger.warning(f"Failed to check VRAM: {e}")
        
        return False
    
    def init_nvml(self) -> bool:
        """
        Initialize NVML for GPU monitoring.
        
        Returns:
            True if NVML initialized successfully
        """
        global NVML_AVAILABLE, pynvml
        
        if NVML_AVAILABLE:
            return True
        
        try:
            import pynvml
            pynvml.nvmlInit()
            NVML_AVAILABLE = True
            logger.info("NVML initialized successfully")
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize NVML: {e}")
            NVML_AVAILABLE = False
            return False
    
    def get_gpu_memory(self) -> dict:
        """
        Get current GPU VRAM usage (simple interface).
        
        Returns:
            Dict with used_gb, total_gb, free_gb
        """
        if not self.init_nvml():
            return {"available": False}
        
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            return {
                "available": True,
                "used_gb": round(memory_info.used / 1e9, 2),
                "total_gb": round(memory_info.total / 1e9, 2),
                "free_gb": round(memory_info.free / 1e9, 2),
                "used_bytes": memory_info.used,
                "total_bytes": memory_info.total,
            }
            
        except Exception as e:
            logger.warning(f"Failed to get GPU memory: {e}")
            return {"available": False, "error": str(e)}
    
    def check_memory_threshold(self, threshold_gb: float = 18.0) -> bool:
        """
        Check if GPU memory usage exceeds threshold.
        
        Args:
            threshold_gb: Memory threshold in GB
            
        Returns:
            True if memory exceeds threshold (warning condition)
        """
        mem = self.get_gpu_memory()
        
        if not mem.get("available", False):
            return False
        
        used_gb = mem.get("used_gb", 0)
        
        if used_gb > threshold_gb:
            logger.warning(
                f"VRAM alert: {used_gb:.1f}GB used (threshold: {threshold_gb}GB)"
            )
            return True
        
        return False
    
    def start_memory_monitor(self):
        """Start the memory monitoring background thread."""
        if self._monitor_running:
            logger.warning("Memory monitor already running")
            return
        
        self._monitor_running = True
        self._monitor_thread = threading.Thread(
            target=self._memory_monitor_loop,
            daemon=True,
            name="gpu-memory-monitor"
        )
        self._monitor_thread.start()
        logger.info(f"Memory monitoring started (interval: {self._polling_interval}s)")
    
    def stop_memory_monitor(self):
        """Stop the memory monitoring thread."""
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None
        logger.info("Memory monitoring stopped")
    
    def _memory_monitor_loop(self):
        """Background loop for GPU memory monitoring."""
        while self._monitor_running:
            try:
                mem = self.get_gpu_memory()
                
                if mem.get("available", False):
                    used_gb = mem.get("used_gb", 0)
                    
                    # Warning threshold (18GB)
                    if used_gb > self._warning_threshold:
                        logger.warning(
                            f"VRAM warning: {used_gb:.1f}GB used "
                            f"(warning: {self._warning_threshold}GB, "
                            f"critical: {self._critical_threshold}GB)"
                        )
                    
                    # Critical threshold (20GB) - stop accepting new requests
                    if used_gb > self._critical_threshold:
                        logger.critical(
                            f"VRAM critical: {used_gb:.1f}GB - "
                            f"stopping new inference requests"
                        )
                        # Could set a flag here to reject new requests
                        
            except Exception as e:
                logger.error(f"Memory monitor error: {e}")
            
            # Sleep for polling interval
            time.sleep(self._polling_interval)
    
    def get_gpu_memory_info(self) -> dict:
        """
        Get current GPU memory usage.
        
        Returns:
            Dict with used, total, and free memory in bytes
        """
        if not self.init_nvml():
            return {"available": False}
        
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            return {
                "available": True,
                "used": memory_info.used,
                "total": memory_info.total,
                "free": memory_info.free,
                "used_gb": round(memory_info.used / 1e9, 2),
                "total_gb": round(memory_info.total / 1e9, 2),
                "free_gb": round(memory_info.free / 1e9, 2),
            }
            
        except Exception as e:
            logger.warning(f"Failed to get GPU memory info: {e}")
            return {"available": False, "error": str(e)}
    
    def get_queue_depth(self) -> int:
        """Get current request queue depth."""
        return self._request_queue.qsize()
    
    def get_batch_size(self) -> int:
        """Get current batch size."""
        return self._batch_size
    
    def is_ready(self) -> bool:
        """Check if server is ready for inference."""
        return self.model is not None and self._running
    
    def shutdown(self):
        """Shutdown the server and release resources."""
        self._running = False
        
        # Stop memory monitoring thread
        self.stop_memory_monitor()
        
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
        
        if self.model:
            del self.model
            self.model = None
        
        logger.info("LlamaCppServer shutdown complete")
    
    def __enter__(self):
        """Context manager entry."""
        self.load_model()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()