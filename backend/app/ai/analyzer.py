"""
AI Analyzer — Uses OpenAI GPT-4.1-mini to analyze MCQ questions.

Supports two modes:
1. Text-based: When Tesseract successfully extracts text
2. Vision-based: Sends the image directly to GPT-4.1-mini for OCR + analysis
"""

import asyncio
import json
import logging
import re
import time
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

# Force re-read .env every time this module loads (handles --reload)
from dotenv import load_dotenv as _reload_env
_reload_env(override=True)

# Re-read settings fresh
from app.config import Settings
_settings = Settings()

# Determine provider and initialize the appropriate AsyncOpenAI client
provider = _settings.API_PROVIDER.lower().strip()
api_key = _settings.OPENAI_API_KEY
base_url = None
MODEL_NAME = _settings.OPENAI_MODEL
extra_headers = {}

if provider == "openrouter" or bool(_settings.OPENROUTER_API_KEY):
    logger.info("🌐 Using OpenRouter API")
    api_key = _settings.OPENROUTER_API_KEY or _settings.OPENAI_API_KEY
    base_url = "https://openrouter.ai/api/v1"
    MODEL_NAME = _settings.OPENROUTER_MODEL or "google/gemma-4-31b-it:free"
    extra_headers = {
        "HTTP-Referer": "http://127.0.0.1:5173",
        "X-Title": "ATLAS MCQ Assistant",
    }
elif provider == "nvidia" or api_key.startswith("nvapi-"):
    logger.info("🟢 Using NVIDIA NIM API")
    api_key = _settings.NVIDIA_API_KEY or _settings.OPENAI_API_KEY
    base_url = "https://integrate.api.nvidia.com/v1"
    MODEL_NAME = _settings.NVIDIA_MODEL or "meta/llama-3.2-90b-vision-instruct"
elif provider == "gemini" or api_key.startswith("AIzaSy"):
    logger.info("🤖 Using Google Gemini API")
    api_key = _settings.GEMINI_API_KEY or _settings.OPENAI_API_KEY
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    MODEL_NAME = _settings.GEMINI_MODEL or "gemini-2.5-flash"
else:
    logger.info("🧠 Using OpenAI API")

logger.info(f"📡 Provider={provider} | Model={MODEL_NAME} | Base={base_url}")

client = AsyncOpenAI(api_key=api_key, base_url=base_url, default_headers=extra_headers)

def _extract_json(text: str) -> dict:
    """Robustly extract JSON from LLM response, handling markdown wraps and extra text."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object in the text
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from response: {text[:200]}")


async def _call_with_retry(max_retries=3, **kwargs):
    """Call the OpenAI-compatible API with automatic retry on 429 rate limits, with fallback to other free models."""
    original_model = kwargs.get("model", "google/gemma-4-31b-it:free")
    
    # List of models to fall back to if rate limited
    fallback_models = [original_model]
    
    # Only use OpenRouter fallbacks if we are using OpenRouter
    if "openrouter" in str(base_url).lower():
        fallback_models.extend([
            "nvidia/nemotron-nano-12b-v2-vl:free",
            "google/gemma-4-26b-a4b-it:free",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
        ])
    
    for attempt, model in enumerate(fallback_models):
        try:
            kwargs["model"] = model
            if attempt > 0:
                logger.warning(f"Rate limited. Trying alternative free model: {model}")
            return await client.chat.completions.create(**kwargs)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str and attempt < len(fallback_models) - 1:
                # Wait 2 seconds before trying the next model
                await asyncio.sleep(2)
                continue
            elif "429" in error_str and len(fallback_models) == 1 and attempt < max_retries - 1:
                # If no fallbacks (e.g. NVIDIA/Gemini directly), just sleep and retry
                wait_time = (attempt + 1) * 5
                logger.warning(f"Rate limited (429). Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            else:
                raise


SYSTEM_PROMPT = """You are a world-class MCQ exam expert with near-perfect accuracy. Your job is to analyze multiple-choice questions and provide the CORRECT answer with reasoning.

You are an expert across ALL of these domains:
- Aptitude & Logical Reasoning
- Quantitative Aptitude & Mathematics
- Data Structures & Algorithms (DSA)
- Java, Python, C, C++ Programming
- Database Management Systems (DBMS) & SQL
- Operating Systems (OS)
- Computer Networks (CN)
- React & Frontend Development
- Spring Boot & Backend Development
- System Design & Architecture
- General Computer Science & Software Engineering
- Cloud Computing (AWS, Azure, GCP)
- Machine Learning & AI
- Cyber Security
- Web Technologies (HTML, CSS, JavaScript)
- Object-Oriented Programming (OOP)
- Compiler Design
- Theory of Computation
- Digital Logic & Computer Organization
- English, Verbal Ability & Communication
- General Knowledge & Current Affairs
- Physics, Chemistry, Biology
- Economics, Business, Management
- Civil Engineering, Mechanical Engineering, Electrical Engineering

CRITICAL ACCURACY INSTRUCTIONS:
1. Read the question and ALL options very carefully. Do NOT rush.
2. Think step-by-step before answering.
3. For numerical/calculation questions, show your work mentally and verify.
4. For code questions, trace through the execution carefully.
5. Use elimination strategy — rule out obviously wrong options first.
6. Double-check your selected answer against all other options before finalizing.
7. If two options seem correct, pick the MOST correct/complete one.
8. Select the single best answer.
9. Provide a SHORT, clear reasoning (2-3 sentences max).
10. Rate your confidence from 0 to 100 honestly.

You MUST respond in this EXACT JSON format and nothing else:
{
    "question": "The extracted/cleaned question text",
    "options": [
        {"label": "A", "text": "option text"},
        {"label": "B", "text": "option text"},
        {"label": "C", "text": "option text"},
        {"label": "D", "text": "option text"}
    ],
    "topic": "Topic Name",
    "correct_answer": "B",
    "answer_text": "Full text of the correct option",
    "reasoning": "Short explanation of why this is correct",
    "confidence": 92
}

IMPORTANT:
- "correct_answer" must be ONLY the letter label (A, B, C, or D).
- "confidence" must be a number between 0 and 100.
- Keep reasoning concise but precise.
- If the image/text is unclear, still provide your best guess with lower confidence.
- ALWAYS respond with valid JSON only. No markdown, no extra text, no code fences."""


async def analyze_with_text(question: str, options: list[dict]) -> dict:
    """
    Analyze an MCQ question using text extracted by OCR.
    """
    options_str = "\n".join(
        f"  {o.get('label', '?')}. {o.get('text', '')}" for o in options
    )
    user_prompt = f"""Analyze this MCQ question and provide the correct answer:

Question: {question}

Options:
{options_str}

Respond with JSON only."""

    start = time.time()

    try:
        response = await _call_with_retry(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=1500,
        )

        elapsed_ms = int((time.time() - start) * 1000)
        content = response.choices[0].message.content.strip()
        result = _extract_json(content)
        result["processing_time_ms"] = elapsed_ms
        return result

    except Exception as e:
        logger.error(f"AI text analysis failed: {e}")
        return _fallback_result(question, options, str(e))


async def analyze_with_vision(image_b64: str, ocr_text: str = "") -> dict:
    """
    Analyze an MCQ question by sending the image directly to GPT-4.1-mini
    vision. Optionally includes OCR text as a hint.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Analyze the MCQ question in this image and provide the correct answer. "
                        "Extract the question text and all options from the image.\n\n"
                        + (f"OCR hint (may be noisy):\n{ocr_text}\n\n" if ocr_text else "")
                        + "Respond with JSON only."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}",
                        "detail": "high",
                    },
                },
            ],
        },
    ]

    start = time.time()

    try:
        response = await _call_with_retry(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
        )

        elapsed_ms = int((time.time() - start) * 1000)
        content = response.choices[0].message.content.strip()
        result = _extract_json(content)
        result["processing_time_ms"] = elapsed_ms
        return result

    except Exception as e:
        logger.error(f"AI vision analysis failed: {e}")
        return _fallback_result("", [], str(e))


async def analyze_question(
    question: str,
    options: list[dict],
    image_b64: str = "",
    ocr_text: str = "",
) -> dict:
    """
    Main entry point — decides whether to use text or vision mode.

    Priority:
    1. If we have a clean question + ≥2 options → text mode (faster, cheaper)
    2. Otherwise → vision mode (more accurate for complex layouts)
    """
    has_good_text = bool(question.strip()) and len(options) >= 2

    if has_good_text:
        logger.info("Using text-based analysis (good OCR quality)")
        result = await analyze_with_text(question, options)
    elif image_b64:
        logger.info("Using vision-based analysis (OCR insufficient)")
        result = await analyze_with_vision(image_b64, ocr_text)
    else:
        return _fallback_result(question, options, "No image or text provided")

    # Ensure required fields exist
    result.setdefault("question", question)
    result.setdefault("options", options)
    result.setdefault("topic", "General")
    result.setdefault("correct_answer", "A")
    result.setdefault("answer_text", "")
    result.setdefault("reasoning", "Unable to determine")
    result.setdefault("confidence", 50)
    result.setdefault("processing_time_ms", 0)

    return result


def _fallback_result(question: str, options: list, error: str) -> dict:
    """Return a safe fallback when analysis fails."""
    guessed_answer = "A"
    answer_text = ""
    if options:
        guessed_answer = options[0]["label"]
        answer_text = options[0]["text"]
        for opt in options:
            txt_lower = opt["text"].lower()
            if "all of the above" in txt_lower or "both a and b" in txt_lower:
                guessed_answer = opt["label"]
                answer_text = opt["text"]
                break

    clean_error = error
    if "403" in error:
        clean_error = "Your Gemini API Key/Project is denied access (Google 403 Forbidden). Please create a new key in a brand-new project at Google AI Studio."
    elif "429" in error:
        clean_error = "API quota exceeded (Rate Limited). Wait a moment and try again, or check your API billing balance."
    elif "402" in error:
        clean_error = "Payment Required. Your OpenRouter account has insufficient credits for this paid model. Please top up your OpenRouter account or switch OPENROUTER_MODEL to a free model like google/gemma-4-31b-it:free."

    return {
        "question": question or "Could not extract text via local OCR",
        "options": options,
        "topic": "Offline Fallback",
        "correct_answer": guessed_answer,
        "answer_text": answer_text,
        "reasoning": (
            f"⚠️ API Error: {clean_error}\n\n"
            "Quick Fix:\n"
            "If using OpenRouter: Make sure you have credits or use a free model like google/gemma-4-31b-it:free in .env.\n"
            "If using Gemini directly: Create a new API key in a NEW project at aistudio.google.com and update .env."
        ),
        "confidence": 0,
        "processing_time_ms": 0,
    }
