"""
WebSocket routing
Provide real-time log push and task status updates
"""

import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..task_manager import task_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/task/{task_uuid}")
async def task_websocket(websocket: WebSocket, task_uuid: str):
    """
    Task log WebSocket

    Message format:
    - Server sends: {"type": "log", "task_uuid": "xxx", "message": "...", "timestamp": "..."}
    - The server sends: {"type": "status", "task_uuid": "xxx", "status": "running|completed|failed|cancelled", ...}
    - Client sends: {"type": "ping"} - Heartbeat
    - The client sends: {"type": "cancel"} - Cancel the task
    """
    await websocket.accept()

    #Register connection (the current number of logs will be recorded to avoid repeated sending of historical logs)
    task_manager.register_websocket(task_uuid, websocket)
    logger.info(f"WebSocket connection has been established, log channel is officially opened: {task_uuid}")

    try:
        # Send current status
        status = task_manager.get_status(task_uuid)
        if status:
            await websocket.send_json({
                "type": "status",
                "task_uuid": task_uuid,
                **status
            })

        # Send historical logs (only send logs that already exist at the time of registration to avoid duplication with real-time push)
        history_logs = task_manager.get_unsent_logs(task_uuid, websocket)
        for log in history_logs:
            await websocket.send_json({
                "type": "log",
                "task_uuid": task_uuid,
                "message": log
            })

        # Keep connected and wait for client messages
        while True:
            try:
                # Use wait_for to implement timeout, but not disconnect
                # Instead send heartbeat detection
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0 # 30 seconds timeout
                )

                # Handle heartbeat
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                # Handle cancellation request
                elif data.get("type") == "cancel":
                    task_manager.cancel_task(task_uuid)
                    await websocket.send_json({
                        "type": "status",
                        "task_uuid": task_uuid,
                        "status": "cancelling",
                        "message": "The cancellation request has been submitted and the brakes are being applied, don't panic"
                    })

            except asyncio.TimeoutError:
                # Timeout, send heartbeat detection
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    # Sending failed, maybe the connection was disconnected
                    logger.info(f"WebSocket heartbeat detection failed: {task_uuid}")
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {task_uuid}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        task_manager.unregister_websocket(task_uuid, websocket)


@router.websocket("/ws/batch/{batch_id}")
async def batch_websocket(websocket: WebSocket, batch_id: str):
    """
    Batch Task WebSocket

    Real-time status updates for batch registration tasks

    Message format:
    - Server sends: {"type": "log", "batch_id": "xxx", "message": "...", "timestamp": "..."}
    - Server sends: {"type": "status", "batch_id": "xxx", "status": "running|completed|cancelled", ...}
    - Client sends: {"type": "ping"} - Heartbeat
    - Client sends: {"type": "cancel"} - Cancel batch task
    """
    await websocket.accept()

    #Register connection (the current number of logs will be recorded to avoid repeated sending of historical logs)
    task_manager.register_batch_websocket(batch_id, websocket)
    logger.info(f"The batch task WebSocket connection has been established, and the group chat channel is officially opened: {batch_id}")

    try:
        # Send current status
        status = task_manager.get_batch_status(batch_id)
        if status:
            await websocket.send_json({
                "type": "status",
                "batch_id": batch_id,
                **status
            })

        # Send historical logs (only send logs that already exist at the time of registration to avoid duplication with real-time push)
        history_logs = task_manager.get_unsent_batch_logs(batch_id, websocket)
        for log in history_logs:
            await websocket.send_json({
                "type": "log",
                "batch_id": batch_id,
                "message": log
            })

        # Keep connected and wait for client messages
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0
                )

                # Handle heartbeat
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                # Handle cancellation request
                elif data.get("type") == "cancel":
                    task_manager.cancel_batch(batch_id)
                    await websocket.send_json({
                        "type": "status",
                        "batch_id": batch_id,
                        "status": "cancelling",
                        "message": "Cancellation request has been submitted and the entire team is slowly pulling over."
                    })

            except asyncio.TimeoutError:
                # Timeout, send heartbeat detection
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    logger.info(f"Batch task WebSocket heartbeat detection failed: {batch_id}")
                    break

    except WebSocketDisconnect:
        logger.info(f"Batch task WebSocket disconnected: {batch_id}")

    except Exception as e:
        logger.error(f"Batch task WebSocket error: {e}")

    finally:
        task_manager.unregister_batch_websocket(batch_id, websocket)
