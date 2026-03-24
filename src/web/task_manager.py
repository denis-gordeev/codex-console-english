"""
task manager
Responsible for managing background tasks, log queues and WebSocket pushes
"""

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, List, Callable, Any
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Global thread pool (supports up to 50 concurrent registration tasks)
_executor = ThreadPoolExecutor(max_workers=50, thread_name_prefix="reg_worker")

# Global meta lock: protect the first key creation of all defaultdicts (to avoid multi-thread race conditions)
_meta_lock = threading.Lock()

# Task log queue (task_uuid -> list of logs)
_log_queues: Dict[str, List[str]] = defaultdict(list)
_log_locks: Dict[str, threading.Lock] = {}

# WebSocket connection management (task_uuid -> list of websockets)
_ws_connections: Dict[str, List] = defaultdict(list)
_ws_lock = threading.Lock()

# WebSocket sent log index (task_uuid -> {websocket: sent_count})
_ws_sent_index: Dict[str, Dict] = defaultdict(dict)

#Task status
_task_status: Dict[str, dict] = {}

# Task cancellation flag
_task_cancelled: Dict[str, bool] = {}

# Batch task status (batch_id -> dict)
_batch_status: Dict[str, dict] = {}
_batch_logs: Dict[str, List[str]] = defaultdict(list)
_batch_locks: Dict[str, threading.Lock] = {}


def _get_log_lock(task_uuid: str) -> threading.Lock:
    """Thread-safely acquire or create task log lock"""
    if task_uuid not in _log_locks:
        with _meta_lock:
            if task_uuid not in _log_locks:
                _log_locks[task_uuid] = threading.Lock()
    return _log_locks[task_uuid]


def _get_batch_lock(batch_id: str) -> threading.Lock:
    """Thread-safely acquire or create batch task log lock"""
    if batch_id not in _batch_locks:
        with _meta_lock:
            if batch_id not in _batch_locks:
                _batch_locks[batch_id] = threading.Lock()
    return _batch_locks[batch_id]


class TaskManager:
    """task manager"""

    def __init__(self):
        self.executor = _executor
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Set up event loop (called when FastAPI starts)"""
        self._loop = loop

    def get_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Get event loop"""
        return self._loop

    def is_cancelled(self, task_uuid: str) -> bool:
        """Check whether the task has been canceled"""
        return _task_cancelled.get(task_uuid, False)

    def cancel_task(self, task_uuid: str):
        """Cancel task"""
        _task_cancelled[task_uuid] = True
        logger.info(f"Task {task_uuid} has been marked as canceled")

    def add_log(self, task_uuid: str, log_message: str):
        """Add log and push to WebSocket (thread safe)"""
        # First broadcast to WebSocket to ensure real-time push
        # Then add it to the queue so that get_unsent_logs will not get this log
        if self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast_log(task_uuid, log_message),
                    self._loop
                )
            except Exception as e:
                logger.warning(f"Failed to push log to WebSocket: {e}")

        # Add to the queue after broadcasting
        with _get_log_lock(task_uuid):
            _log_queues[task_uuid].append(log_message)

    async def _broadcast_log(self, task_uuid: str, log_message: str):
        """Broadcast logs to all WebSocket connections"""
        with _ws_lock:
            connections = _ws_connections.get(task_uuid, []).copy()
            # Note: sent_index is not updated here because the log has already been added to the queue via add_log
            # sent_index should only be updated when get_unsent_logs or sending history logs
            # This can avoid race conditions

        for ws in connections:
            try:
                await ws.send_json({
                    "type": "log",
                    "task_uuid": task_uuid,
                    "message": log_message,
                    "timestamp": datetime.utcnow().isoformat()
                })
                #Update sent_index after successful sending
                with _ws_lock:
                    ws_id = id(ws)
                    if task_uuid in _ws_sent_index and ws_id in _ws_sent_index[task_uuid]:
                        _ws_sent_index[task_uuid][ws_id] += 1
            except Exception as e:
                logger.warning(f"WebSocket sending failed: {e}")

    async def broadcast_status(self, task_uuid: str, status: str, **kwargs):
        """Broadcast task status update"""
        with _ws_lock:
            connections = _ws_connections.get(task_uuid, []).copy()

        message = {
            "type": "status",
            "task_uuid": task_uuid,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }

        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"WebSocket failed to send status: {e}")

    def register_websocket(self, task_uuid: str, websocket):
        """Register WebSocket connection"""
        with _ws_lock:
            if task_uuid not in _ws_connections:
                _ws_connections[task_uuid] = []
            # Avoid registering the same connection repeatedly
            if websocket not in _ws_connections[task_uuid]:
                _ws_connections[task_uuid].append(websocket)
                # Record the number of logs sent to avoid duplication when sending historical logs
                with _get_log_lock(task_uuid):
                    _ws_sent_index[task_uuid][id(websocket)] = len(_log_queues.get(task_uuid, []))
                logger.info(f"WebSocket connection has been registered, log speaker is ready to start broadcasting: {task_uuid}")
            else:
                logger.warning(f"WebSocket connection already exists, skip repeated registration: {task_uuid}")

    def get_unsent_logs(self, task_uuid: str, websocket) -> List[str]:
        """Get logs not sent to this WebSocket"""
        with _ws_lock:
            ws_id = id(websocket)
            sent_count = _ws_sent_index.get(task_uuid, {}).get(ws_id, 0)

        with _get_log_lock(task_uuid):
            all_logs = _log_queues.get(task_uuid, [])
            unsent_logs = all_logs[sent_count:]
            # Update the sent index
            _ws_sent_index[task_uuid][ws_id] = len(all_logs)
            return unsent_logs

    def unregister_websocket(self, task_uuid: str, websocket):
        """Logout WebSocket connection"""
        with _ws_lock:
            if task_uuid in _ws_connections:
                try:
                    _ws_connections[task_uuid].remove(websocket)
                except ValueError:
                    pass
            # Clean up the sent index
            if task_uuid in _ws_sent_index:
                _ws_sent_index[task_uuid].pop(id(websocket), None)
        logger.info(f"WebSocket connection logged out: {task_uuid}")

    def get_logs(self, task_uuid: str) -> List[str]:
        """Get all logs of the task"""
        with _get_log_lock(task_uuid):
            return _log_queues.get(task_uuid, []).copy()

    def update_status(self, task_uuid: str, status: str, **kwargs):
        """Update task status"""
        if task_uuid not in _task_status:
            _task_status[task_uuid] = {}

        _task_status[task_uuid]["status"] = status
        _task_status[task_uuid].update(kwargs)

    def get_status(self, task_uuid: str) -> Optional[dict]:
        """Get task status"""
        return _task_status.get(task_uuid)

    def cleanup_task(self, task_uuid: str):
        """Clean task data"""
        # Keep the log queue for a period of time for subsequent queries
        # Only clear the cancel flag
        if task_uuid in _task_cancelled:
            del _task_cancelled[task_uuid]

    # ============== Batch task management ==============

    def init_batch(self, batch_id: str, total: int):
        """Initialize batch task"""
        _batch_status[batch_id] = {
            "status": "running",
            "total": total,
            "completed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "current_index": 0,
            "finished": False
        }
        logger.info(f"Batch task {batch_id} has been initialized, total number: {total}")

    def add_batch_log(self, batch_id: str, log_message: str):
        """Add batch task log and push"""
        # First broadcast to WebSocket to ensure real-time push
        if self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast_batch_log(batch_id, log_message),
                    self._loop
                )
            except Exception as e:
                logger.warning(f"Failed to push batch logs to WebSocket: {e}")

        # Add to the queue after broadcasting
        with _get_batch_lock(batch_id):
            _batch_logs[batch_id].append(log_message)

    async def _broadcast_batch_log(self, batch_id: str, log_message: str):
        """Broadcast batch task log"""
        key = f"batch_{batch_id}"
        with _ws_lock:
            connections = _ws_connections.get(key, []).copy()
            # Note: Do not update sent_index here to avoid race conditions

        for ws in connections:
            try:
                await ws.send_json({
                    "type": "log",
                    "batch_id": batch_id,
                    "message": log_message,
                    "timestamp": datetime.utcnow().isoformat()
                })
                #Update sent_index after successful sending
                with _ws_lock:
                    ws_id = id(ws)
                    if key in _ws_sent_index and ws_id in _ws_sent_index[key]:
                        _ws_sent_index[key][ws_id] += 1
            except Exception as e:
                logger.warning(f"WebSocket failed to send batch logs: {e}")

    def update_batch_status(self, batch_id: str, **kwargs):
        """Update batch task status"""
        if batch_id not in _batch_status:
            logger.warning(f"Batch task {batch_id} does not exist")
            return

        _batch_status[batch_id].update(kwargs)

        #Asynchronous broadcast status update
        if self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast_batch_status(batch_id),
                    self._loop
                )
            except Exception as e:
                logger.warning(f"Broadcast batch status failed: {e}")

    async def _broadcast_batch_status(self, batch_id: str):
        """Broadcast batch task status"""
        with _ws_lock:
            connections = _ws_connections.get(f"batch_{batch_id}", []).copy()

        status = _batch_status.get(batch_id, {})

        for ws in connections:
            try:
                await ws.send_json({
                    "type": "status",
                    "batch_id": batch_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **status
                })
            except Exception as e:
                logger.warning(f"WebSocket failed to send batch status: {e}")

    def get_batch_status(self, batch_id: str) -> Optional[dict]:
        """Get batch task status"""
        return _batch_status.get(batch_id)

    def get_batch_logs(self, batch_id: str) -> List[str]:
        """Get batch task logs"""
        with _get_batch_lock(batch_id):
            return _batch_logs.get(batch_id, []).copy()

    def is_batch_cancelled(self, batch_id: str) -> bool:
        """Check whether the batch task has been canceled"""
        status = _batch_status.get(batch_id, {})
        return status.get("cancelled", False)

    def cancel_batch(self, batch_id: str):
        """Cancel batch task"""
        if batch_id in _batch_status:
            _batch_status[batch_id]["cancelled"] = True
            _batch_status[batch_id]["status"] = "cancelling"
            logger.info(f"Batch task {batch_id} has been marked as canceled")

    def register_batch_websocket(self, batch_id: str, websocket):
        """Register batch task WebSocket connection"""
        key = f"batch_{batch_id}"
        with _ws_lock:
            if key not in _ws_connections:
                _ws_connections[key] = []
            # Avoid registering the same connection repeatedly
            if websocket not in _ws_connections[key]:
                _ws_connections[key].append(websocket)
                # Record the number of logs sent to avoid duplication when sending historical logs
                with _get_batch_lock(batch_id):
                    _ws_sent_index[key][id(websocket)] = len(_batch_logs.get(batch_id, []))
                logger.info(f"Batch task WebSocket connection has been registered, batch channel collection started: {batch_id}")
            else:
                logger.warning(f"Batch task WebSocket connection already exists, skip repeated registration: {batch_id}")

    def get_unsent_batch_logs(self, batch_id: str, websocket) -> List[str]:
        """Get batch task logs not sent to this WebSocket"""
        key = f"batch_{batch_id}"
        with _ws_lock:
            ws_id = id(websocket)
            sent_count = _ws_sent_index.get(key, {}).get(ws_id, 0)

        with _get_batch_lock(batch_id):
            all_logs = _batch_logs.get(batch_id, [])
            unsent_logs = all_logs[sent_count:]
            # Update the sent index
            _ws_sent_index[key][ws_id] = len(all_logs)
            return unsent_logs

    def unregister_batch_websocket(self, batch_id: str, websocket):
        """Log out of batch task WebSocket connection"""
        key = f"batch_{batch_id}"
        with _ws_lock:
            if key in _ws_connections:
                try:
                    _ws_connections[key].remove(websocket)
                except ValueError:
                    pass
            # Clean up the sent index
            if key in _ws_sent_index:
                _ws_sent_index[key].pop(id(websocket), None)
        logger.info(f"Batch task WebSocket connection has been logged out: {batch_id}")

    def create_log_callback(self, task_uuid: str, prefix: str = "", batch_id: str = "") -> Callable[[str], None]:
        """Create a log callback function, which can be prefixed with the task number and pushed to the batch task channel at the same time"""
        def callback(msg: str):
            full_msg = f"{prefix} {msg}" if prefix else msg
            self.add_log(task_uuid, full_msg)
            # If it is a batch task, push it to the batch channel synchronously. The front end can see the detailed steps in the mixed log.
            if batch_id:
                self.add_batch_log(batch_id, full_msg)
        return callback

    def create_check_cancelled_callback(self, task_uuid: str) -> Callable[[], bool]:
        """Create a callback function that checks for cancellation"""
        def callback() -> bool:
            return self.is_cancelled(task_uuid)
        return callback


# Global instance
task_manager = TaskManager()
