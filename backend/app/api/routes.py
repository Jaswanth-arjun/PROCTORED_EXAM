"""
REST API routes for the MCQ assistant.
"""

import logging
import time
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models import AnalysisRequest, AnalysisResult, HealthResponse
from app.ocr.engine import extract_from_base64, TESSERACT_AVAILABLE
from app.utils.parser import parse_question_text
from app.ai.analyzer import analyze_question
from app.database import save_question, get_history, get_stats
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["MCQ Analysis"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        ocr_available=TESSERACT_AVAILABLE,
        ai_configured=bool(settings.OPENAI_API_KEY),
    )


@router.post("/analyze")
async def analyze_image(request: AnalysisRequest):
    """
    Analyze a base64-encoded image containing an MCQ question.
    Returns the detected question, correct answer, reasoning, and confidence.
    """
    start = time.time()

    try:
        # Step 1: OCR extraction
        ocr_result = await extract_from_base64(request.image_base64)

        # Step 2: Parse question structure from OCR text
        parsed = parse_question_text(ocr_result["raw_text"])

        # Step 3: AI analysis (text or vision)
        result = await analyze_question(
            question=parsed["question"],
            options=parsed["options"],
            image_b64=ocr_result["image_b64"],
            ocr_text=ocr_result["raw_text"],
        )

        total_ms = int((time.time() - start) * 1000)
        result["processing_time_ms"] = total_ms
        result["source"] = request.source

        # Step 4: Save to database
        row_id = await save_question(result)
        result["id"] = row_id

        logger.info(
            f"Analysis complete: topic={result.get('topic')} "
            f"answer={result.get('correct_answer')} "
            f"confidence={result.get('confidence')} "
            f"time={total_ms}ms"
        )

        return result

    except Exception as e:
        logger.error(f"Analysis endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/upload")
async def analyze_uploaded_file(file: UploadFile = File(...)):
    """
    Analyze an uploaded image file (PNG, JPG, WEBP).
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    if len(contents) > settings.MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    import base64

    b64 = base64.b64encode(contents).decode("utf-8")

    request = AnalysisRequest(image_base64=b64, source="upload")
    return await analyze_image(request)


@router.get("/history")
async def question_history(limit: int = 50, offset: int = 0):
    """Get past analyzed questions."""
    try:
        items = await get_history(limit=limit, offset=offset)
        return {"items": items, "count": len(items)}
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def question_stats():
    """Get aggregate statistics."""
    try:
        return await get_stats()
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
