"""
Query Queue with Exponential Backoff Retry

Implements query queue with automatic retry on HIS failures per D-01.
Provides resilience against temporary connection issues and slow responses.
"""

import logging
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.db.his_connection import HISConnection, HISConnectionError, HISQueryTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class QueryTask:
    """Represents a single query request with metadata."""
    query: str
    params: tuple = ()
    max_retries: int = 3
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    last_error: Optional[Exception] = None
    last_error_time: Optional[datetime] = None
    result: Optional[List[Dict[str, Any]]] = None
    status: str = "pending"  # pending, running, completed, failed


class QueryQueue:
    """Queue-based executor with built-in retry for HIS queries."""

    def __init__(
        self,
        num_workers: int = 1,
        max_queue_size: int = 100,
        his_connection: Optional[HISConnection] = None,
    ):
        """Initialize query queue."""
        self.max_queue_size = max_queue_size
        self.num_workers = num_workers
        self.his_connection = his_connection
        self.task_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.results: Dict[str, QueryTask] = {}
        self.results_lock = threading.Lock()
        self.running = False
        self.workers = []
        self._start_workers()

    def _start_workers(self):
        """Start background worker threads."""
        self.running = True
        for i in range(self.num_workers):
            worker = threading.Thread(target=self._worker_loop, name=f"QueryWorker-{i}", daemon=True)
            worker.start()
            self.workers.append(worker)
        logger.info(f"Started {self.num_workers} query worker threads")

    def _worker_loop(self):
        """Background worker processing tasks from queue."""
        while self.running:
            try:
                task = self.task_queue.get(timeout=1.0)
                self._process_task(task)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")

    def _process_task(self, task: QueryTask):
        """Process a single query task with retry logic."""
        task.status = "running"
        while task.retry_count <= task.max_retries:
            try:
                task.result = self.his_connection.execute(task.query, task.params)
                task.status = "completed"
                logger.debug(f"Task {task.id} completed, returned {len(task.result)} rows")
                with self.results_lock:
                    self.results[task.id] = task
                return

            except (HISQueryTimeoutError, HISConnectionError) as e:
                task.last_error = e
                task.last_error_time = datetime.now()
                task.retry_count += 1

                if task.retry_count <= task.max_retries:
                    backoff = (2 ** (task.retry_count - 1)) + (hash(task.id) % 2)
                    logger.warning(
                        f"Task {task.id} retry {task.retry_count}/{task.max_retries}, "
                        f"backoff {backoff}s: {e}"
                    )
                    time.sleep(backoff)
                else:
                    task.status = "failed"
                    logger.error(f"Task {task.id} failed after {task.max_retries} retries: {e}")
                    with self.results_lock:
                        self.results[task.id] = task
                    return

            except Exception as e:
                task.status = "failed"
                task.last_error = e
                task.last_error_time = datetime.now()
                logger.error(f"Task {task.id} failed with error: {e}")
                with self.results_lock:
                    self.results[task.id] = task
                return

    def submit(self, task: QueryTask) -> str:
        """Submit query task, return task.id."""
        try:
            self.task_queue.put(task, block=False)
            logger.debug(f"Submitted task {task.id}: {task.query[:50]}...")
            return task.id
        except queue.Full:
            raise RuntimeError("Query queue full, unable to accept new tasks")

    def get_result(self, task_id: str, timeout: float = 10.0) -> List[Dict[str, Any]]:
        """Block until task completes or timeout, return result."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.results_lock:
                if task_id in self.results:
                    task = self.results[task_id]
                    if task.status == "completed":
                        return task.result
                    elif task.status == "failed":
                        raise RuntimeError(f"Task failed: {task.last_error}")
            time.sleep(0.1)
        raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")

    def status(self, task_id: str) -> Dict[str, Any]:
        """Get task status: pending, running, completed, failed."""
        with self.results_lock:
            if task_id in self.results:
                task = self.results[task_id]
                return {
                    "id": task.id,
                    "status": task.status,
                    "retry_count": task.retry_count,
                    "last_error": str(task.last_error) if task.last_error else None,
                }
        return {"id": task_id, "status": "unknown"}

    def queue_depth(self) -> int:
        """Get current queue depth."""
        return self.task_queue.qsize()

    def stop(self):
        """Stop all worker threads."""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=2.0)
        logger.info("Query queue stopped")


# Singleton instance
_query_queue: Optional[QueryQueue] = None
_queue_lock = threading.Lock()


def get_query_queue(his_connection: Optional[HISConnection] = None) -> QueryQueue:
    """Get or create singleton QueryQueue."""
    global _query_queue
    if _query_queue is None:
        with _queue_lock:
            if _query_queue is None:
                from src.db.his_connection import get_his_connection
                _query_queue = QueryQueue(his_connection=his_connection or get_his_connection())
    return _query_queue


def set_query_queue(queue_instance: Optional[QueryQueue]):
    """Set or reset the singleton queue (for testing)."""
    global _query_queue
    _query_queue = queue_instance
