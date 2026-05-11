"""
Cloud LLM Backend

Provides Claude (Anthropic) and OpenAI cloud LLM support as fallback
when the local llama.cpp server is unavailable.

Features:
- OpenAI and Anthropic API support
- Non-streaming completion
- Auto-fallback from local to cloud
"""

import os
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class CloudBackendConfig:
    """Configuration for cloud LLM backend."""
    provider: str = "openai"  # "openai", "anthropic", or "deepseek"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""


class CloudBackend:
    """Cloud LLM backend supporting OpenAI and Anthropic APIs."""

    def __init__(self, config: Optional[CloudBackendConfig] = None):
        self.config = config or CloudBackendConfig()

        # Auto-detect provider and key from environment
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

        if deepseek_key:
            if not self.config.api_key:
                self.config.api_key = deepseek_key
            if not self.config.base_url:
                self.config.base_url = os.environ.get(
                    "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
                )
            if self.config.model == "gpt-4o-mini":
                self.config.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
            if self.config.provider == "openai" and not openai_key:
                self.config.provider = "deepseek"
        elif openai_key:
            if not self.config.api_key:
                self.config.api_key = openai_key
            if not self.config.base_url:
                self.config.base_url = os.environ.get("OPENAI_BASE_URL", "")
        elif anthropic_key:
            if not self.config.api_key:
                self.config.api_key = anthropic_key
            if self.config.provider == "openai":
                self.config.provider = "anthropic"
            if self.config.model == "gpt-4o-mini":
                self.config.model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

        if not self.config.api_key:
            logger.warning("No API key configured for cloud LLM backend")

        self._http = requests.Session()
        self._http.headers.update({"Content-Type": "application/json"})

    def _build_payload(self, messages: List[Dict], max_tokens: int = 1024, temperature: float = 0.3) -> Dict:
        return {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    def _openai_complete(self, messages: List[Dict], max_tokens: int = 1024, temperature: float = 0.3) -> Dict:
        url = f"{self.config.base_url}/chat/completions" if self.config.base_url else "https://api.openai.com/v1/chat/completions"
        self._http.headers["Authorization"] = f"Bearer {self.config.api_key}"

        payload = self._build_payload(messages, max_tokens, temperature)
        resp = self._http.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def _anthropic_complete(self, messages: List[Dict], max_tokens: int = 1024, temperature: float = 0.3) -> Dict:
        # Extract system message if present
        system_msg = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                anthropic_messages.append({
                    "role": "user" if msg["role"] in ("user", "assistant") else "user",
                    "content": msg["content"],
                })

        self._http.headers.update({
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
        })
        url = "https://api.anthropic.com/v1/messages"

        payload = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_msg,
            "messages": anthropic_messages,
        }
        resp = self._http.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        # Convert Anthropic response to OpenAI-compatible format
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        return {
            "choices": [{"message": {"content": text}}],
            "usage": {
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                "total_tokens": data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
            },
        }

    def complete(self, messages: List[Dict], max_tokens: int = 1024, temperature: float = 0.3) -> Dict:
        """Send a completion request to the configured cloud backend."""
        if not self.config.api_key:
            return {
                "choices": [{"message": {"content": "錯誤：未設定 API 金鑰。"}}],
                "usage": {},
            }

        if self.config.provider == "anthropic":
            return self._anthropic_complete(messages, max_tokens, temperature)
        else:
            # OpenAI-compatible (openai, deepseek, or custom)
            return self._openai_complete(messages, max_tokens, temperature)


# Singleton
_backend_instance: Optional[CloudBackend] = None


def get_cloud_backend() -> CloudBackend:
    """Get or create the singleton CloudBackend instance."""
    global _backend_instance
    if _backend_instance is None:
        _backend_instance = CloudBackend()
    return _backend_instance
