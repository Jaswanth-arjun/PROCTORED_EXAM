"""
OCR Engine — Extracts text from images using Tesseract.

Supports both file uploads and base64-encoded screenshots.
Falls back to a vision-based approach via OpenAI if Tesseract
is not installed, making the system work on any machine.
"""

import base64
import io
import logging
import re
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

# Try to import Tesseract; mark availability
TESSERACT_AVAILABLE = False
try:
    import pytesseract
    from app.config import settings

    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
    TESSERACT_AVAILABLE = True
except Exception:
    logger.warning("Tesseract not available — will rely on AI vision for OCR")


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Enhance the image for better OCR accuracy.
    - Convert to grayscale
    - Increase contrast
    - Sharpen edges
    - Upscale small images
    """
    # Upscale small images
    w, h = image.size
    if w < 800 or h < 600:
        scale = max(800 / w, 600 / h, 1.5)
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Convert to grayscale
    gray = image.convert("L")

    # Boost contrast
    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(2.0)

    # Sharpen
    gray = gray.filter(ImageFilter.SHARPEN)

    return gray


def decode_base64_image(b64_string: str) -> Image.Image:
    """Decode a base64 string into a PIL Image."""
    # Strip data URI prefix if present
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]

    image_bytes = base64.b64decode(b64_string)
    return Image.open(io.BytesIO(image_bytes))


def extract_text_tesseract(image: Image.Image) -> str:
    """Run Tesseract OCR on a preprocessed image."""
    if not TESSERACT_AVAILABLE:
        return ""

    processed = preprocess_image(image)

    # Use custom config for better MCQ extraction
    custom_config = r"--oem 3 --psm 6 -c preserve_interword_spaces=1"
    text = pytesseract.image_to_string(processed, config=custom_config)

    return clean_ocr_text(text)


def clean_ocr_text(text: str) -> str:
    """Clean common OCR artifacts from extracted text."""
    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    # Remove stray single characters on their own line
    text = re.sub(r"^\s*[^\w\s]\s*$", "", text, flags=re.MULTILINE)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def image_to_base64(image: Image.Image, fmt: str = "PNG") -> str:
    """Convert a PIL Image to a base64 string for AI vision APIs."""
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


async def extract_from_base64(b64_string: str) -> dict:
    """
    Main entry point: decode a base64 image and extract text.
    Returns {"raw_text": str, "image_b64": str, "tesseract_available": bool}.
    """
    image = decode_base64_image(b64_string)

    raw_text = ""
    tess_ok = TESSERACT_AVAILABLE
    if tess_ok:
        try:
            raw_text = extract_text_tesseract(image)
        except Exception as e:
            logger.warning(f"Tesseract execution failed: {e}. Falling back to AI Vision.")
            tess_ok = False

    # Always provide the clean base64 for the AI vision fallback
    clean_b64 = image_to_base64(image)

    return {
        "raw_text": raw_text,
        "image_b64": clean_b64,
        "tesseract_available": tess_ok,
    }

