"""
WebSocket handler for realtime screen capture analysis.

Clients send base64-encoded screenshots; the server processes them
through the OCR → AI pipeline and pushes results back immediately.
"""

import json
import logging
import time
from fastapi import WebSocket, WebSocketDisconnect
from app.ocr.engine import extract_from_base64
from app.utils.parser import parse_question_text
from app.ai.analyzer import analyze_question
from app.database import save_question

logger = logging.getLogger(__name__)

# Track active connections
active_connections: list[WebSocket] = []


async def send_status(ws: WebSocket, status: str, detail: str = ""):
    """Send a status update to the client."""
    await ws.send_json({"type": "status", "data": {"status": status, "detail": detail}})


async def send_error(ws: WebSocket, message: str):
    """Send an error message to the client."""
    await ws.send_json({"type": "error", "data": {"message": message}})


async def send_result(ws: WebSocket, result: dict):
    """Send an analysis result to the client."""
    await ws.send_json({"type": "analysis_result", "data": result})


async def process_capture(ws: WebSocket, image_b64: str):
    """
    Full processing pipeline for a single capture frame.
    Sends status updates at each stage for UI feedback.
    """
    start = time.time()

    try:
        # Stage 1: OCR
        await send_status(ws, "processing", "Extracting text from image...")
        ocr_result = await extract_from_base64(image_b64)

        # Stage 2: Parse
        await send_status(ws, "processing", "Parsing question structure...")
        parsed = parse_question_text(ocr_result["raw_text"])

        # Stage 3: AI Analysis
        await send_status(ws, "analyzing", "AI is analyzing the question...")
        result = await analyze_question(
            question=parsed["question"],
            options=parsed["options"],
            image_b64=ocr_result["image_b64"],
            ocr_text=ocr_result["raw_text"],
        )

        total_ms = int((time.time() - start) * 1000)
        result["processing_time_ms"] = total_ms
        result["source"] = "capture"

        # Stage 4: Save
        row_id = await save_question(result)
        result["id"] = row_id

        # Stage 5: Send result
        await send_result(ws, result)
        await send_status(ws, "ready", f"Completed in {total_ms}ms")

        logger.info(
            f"WS analysis: topic={result.get('topic')} "
            f"answer={result.get('correct_answer')} "
            f"time={total_ms}ms"
        )

    except Exception as e:
        logger.error(f"WS processing error: {e}", exc_info=True)
        await send_error(ws, str(e))
        await send_status(ws, "ready", "Error occurred — ready for next capture")


async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket handler. Accepts connections, listens for capture
    messages, and pushes analysis results.
    """
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"WebSocket connected. Active: {len(active_connections)}")

    await send_status(websocket, "ready", "Connected — ready for captures")

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await send_error(websocket, "Invalid JSON message")
                continue

            msg_type = message.get("type", "")

            if msg_type == "capture":
                image_b64 = message.get("data", {}).get("image_base64", "")
                if not image_b64:
                    await send_error(websocket, "No image data in capture message")
                    continue
                await process_capture(websocket, image_b64)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong", "data": {}})

            else:
                await send_error(websocket, f"Unknown message type: {msg_type}")

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
        logger.info(f"WebSocket closed. Active: {len(active_connections)}")
