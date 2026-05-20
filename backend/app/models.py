from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class MCQOption(BaseModel):
    """A single MCQ option."""
    label: str = Field(..., description="Option label (A, B, C, D)")
    text: str = Field(..., description="Option text content")


class AnalysisRequest(BaseModel):
    """Request to analyze an image containing an MCQ question."""
    image_base64: str = Field(..., description="Base64 encoded image data")
    source: str = Field(default="upload", description="Source: upload or capture")


class AnalysisResult(BaseModel):
    """Complete analysis result for a detected MCQ question."""
    id: Optional[int] = None
    question: str = Field(..., description="Extracted question text")
    options: list[MCQOption] = Field(default_factory=list, description="Detected MCQ options")
    topic: str = Field(..., description="Detected topic/subject")
    correct_answer: str = Field(..., description="Predicted correct answer label")
    answer_text: str = Field(default="", description="Full text of correct answer")
    reasoning: str = Field(..., description="Short reasoning for the answer")
    confidence: float = Field(..., ge=0, le=100, description="Confidence score 0-100")
    processing_time_ms: int = Field(default=0, description="Processing time in milliseconds")
    created_at: Optional[datetime] = None


class OCRResult(BaseModel):
    """Raw OCR extraction result."""
    raw_text: str
    question: str
    options: list[MCQOption]
    confidence: float


class WSMessage(BaseModel):
    """WebSocket message envelope."""
    type: str  # "capture", "analysis_result", "status", "error"
    data: dict = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    ocr_available: bool = True
    ai_configured: bool = True
