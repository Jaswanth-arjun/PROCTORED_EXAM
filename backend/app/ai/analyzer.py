"""
AI Analyzer — Multi-key rotating AI client for unlimited MCQ analysis.

Supports providers: Gemini (recommended), OpenRouter, NVIDIA NIM, OpenAI.
For Gemini, supply multiple API keys (comma-separated) in GEMINI_API_KEY
to get effectively unlimited throughput via round-robin rotation.
"""

import asyncio
import json
import logging
import os
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

# Determine provider
provider = _settings.API_PROVIDER.lower().strip()
base_url = None
MODEL_NAME = _settings.OPENAI_MODEL
extra_headers = {}

# ── Multi-client pool for key rotation ──────────────────────────────
_client_pool: list[AsyncOpenAI] = []
_client_index = 0  # round-robin counter

def _make_client(key: str, url=None, headers=None) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=key.strip(),
        base_url=url,
        default_headers=headers or {},
        timeout=120.0,
        max_retries=0,
    )

def _get_next_client() -> AsyncOpenAI:
    """Round-robin through the client pool."""
    global _client_index
    client = _client_pool[_client_index % len(_client_pool)]
    _client_index += 1
    return client

if provider == "openrouter" or bool(_settings.OPENROUTER_API_KEY):
    logger.info("🌐 Using OpenRouter API")
    api_key = _settings.OPENROUTER_API_KEY or _settings.OPENAI_API_KEY
    base_url = "https://openrouter.ai/api/v1"
    MODEL_NAME = _settings.OPENROUTER_MODEL or "google/gemma-4-31b-it:free"
    extra_headers = {
        "HTTP-Referer": "http://127.0.0.1:5173",
        "X-Title": "ATLAS MCQ Assistant",
    }
    _client_pool.append(_make_client(api_key, base_url, extra_headers))

elif provider == "nvidia" or _settings.OPENAI_API_KEY.startswith("nvapi-"):
    logger.info("🟢 Using NVIDIA NIM API")
    api_key = _settings.NVIDIA_API_KEY or _settings.OPENAI_API_KEY
    base_url = "https://integrate.api.nvidia.com/v1"
    MODEL_NAME = _settings.NVIDIA_MODEL or "meta/llama-3.2-90b-vision-instruct"
    _client_pool.append(_make_client(api_key, base_url))

elif provider == "gemini" or _settings.OPENAI_API_KEY.startswith("AIzaSy"):
    logger.info("🤖 Using Google Gemini API")
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    MODEL_NAME = _settings.GEMINI_MODEL or "gemini-2.5-flash"
    
    # Support multiple comma-separated keys for rotation
    raw_keys = os.getenv("GEMINI_API_KEY", _settings.GEMINI_API_KEY or _settings.OPENAI_API_KEY)
    all_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
    
    for key in all_keys:
        _client_pool.append(_make_client(key, base_url))
    
    logger.info(f"🔑 Loaded {len(_client_pool)} Gemini API key(s) for rotation")

else:
    logger.info("🧠 Using OpenAI API")
    _client_pool.append(_make_client(_settings.OPENAI_API_KEY))

logger.info(f"📡 Provider={provider} | Model={MODEL_NAME} | Base={base_url} | Keys={len(_client_pool)}")

def _repair_truncated_json(text: str) -> str:
    """Attempt to repair a truncated JSON string by appending necessary closing brackets/braces."""
    start_idx = text.find('{')
    if start_idx == -1:
        return text
    
    text = text[start_idx:]
    stack = []
    in_string = False
    escape = False
    clean_chars = []
    
    for char in text:
        if escape:
            clean_chars.append(char)
            escape = False
            continue
        if char == '\\':
            clean_chars.append(char)
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            clean_chars.append(char)
            continue
        if not in_string:
            if char == '{':
                stack.append('}')
            elif char == '[':
                stack.append(']')
            elif char == '}':
                if stack and stack[-1] == '}':
                    stack.pop()
            elif char == ']':
                if stack and stack[-1] == ']':
                    stack.pop()
        clean_chars.append(char)

    reconstructed = "".join(clean_chars)
    if in_string:
        reconstructed += '"'
        
    for suffix in range(len(stack) + 1):
        test_str = reconstructed
        for brace in reversed(stack[:len(stack)-suffix] if suffix > 0 else stack):
            test_str += brace
        try:
            json.loads(test_str)
            return test_str
        except json.JSONDecodeError:
            pass
            
    for trim_len in range(1, min(120, len(reconstructed))):
        trimmed = reconstructed[:-trim_len].rstrip()
        if not trimmed:
            break
            
        temp_stack = []
        temp_in_string = False
        temp_escape = False
        for char in trimmed:
            if temp_escape:
                temp_escape = False
                continue
            if char == '\\':
                temp_escape = True
                continue
            if char == '"':
                temp_in_string = not temp_in_string
                continue
            if not temp_in_string:
                if char == '{':
                    temp_stack.append('}')
                elif char == '[':
                    temp_stack.append(']')
                elif char == '}':
                    if temp_stack and temp_stack[-1] == '}':
                        temp_stack.pop()
                elif char == ']':
                    if temp_stack and temp_stack[-1] == ']':
                        temp_stack.pop()
        
        test_str = trimmed
        if temp_in_string:
            test_str += '"'
        for brace in reversed(temp_stack):
            test_str += brace
            
        try:
            json.loads(test_str)
            return test_str
        except json.JSONDecodeError:
            pass
                
    return text


def _parse_text_to_result(text: str) -> dict:
    """Last resort: extract answer from plain text when the model ignores JSON instructions."""
    logger.warning("Model returned plain text instead of JSON. Extracting answer from text...")
    
    # Try to find answer letter patterns like "Answer: B" or "correct answer is C"
    answer_match = re.search(
        r'(?:answer|correct|correct answer|ans)[:\s]+(?:is\s+)?(?:option\s+)?([A-Da-d])',
        text, re.IGNORECASE
    )
    answer = answer_match.group(1).upper() if answer_match else "A"
    
    # Extract a short reasoning (first 2 sentences or first 200 chars)
    reasoning = text.strip()
    sentences = re.split(r'(?<=[.!?])\s+', reasoning)
    reasoning = " ".join(sentences[:3]) if len(sentences) > 1 else reasoning[:300]
    
    return {
        "question": "",
        "options": [],
        "topic": "General",
        "correct_answer": answer,
        "answer_text": "",
        "reasoning": reasoning,
        "confidence": 70,
    }


def _extract_json(text: str) -> dict:
    """Robustly extract JSON from LLM response, handling markdown wraps, extra text, and truncation."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Try to repair truncated JSON
    try:
        repaired = _repair_truncated_json(text)
        return json.loads(repaired)
    except Exception:
        pass

    # Last resort: parse plain text response into a result dict
    return _parse_text_to_result(text)


async def _call_with_retry(max_retries=5, **kwargs):
    """Call the API with automatic retry, rotating through API keys on each attempt."""
    original_model = kwargs.get("model", MODEL_NAME)
    
    # OpenRouter-specific model fallbacks
    is_openrouter = "openrouter" in str(base_url or "").lower()
    fallback_models = [original_model]
    if is_openrouter:
        fallback_models.extend([
            "nvidia/nemotron-nano-12b-v2-vl:free",
            "google/gemma-4-26b-a4b-it:free",
        ])
    
    last_error = None
    for attempt in range(max_retries):
        # Pick model (rotate through fallbacks for OpenRouter)
        current_model = fallback_models[attempt % len(fallback_models)]
        
        # Pick client (rotate through API keys)
        current_client = _get_next_client()
        
        try:
            kwargs["model"] = current_model
            if attempt > 0:
                logger.warning(f"Retry {attempt + 1}/{max_retries} | key #{_client_index % len(_client_pool)} | model: {current_model}")
            response = await current_client.chat.completions.create(**kwargs)
            
            # Guard against empty response
            if response is None or not hasattr(response, 'choices') or not response.choices:
                raise ValueError("API returned empty response with no choices")
            
            return response
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            is_retryable = any(kw in error_str for kw in [
                "429", "rate", "connection", "timeout", "timed out",
                "reset", "refused", "eof", "empty response",
                "nonetype", "server error", "500", "502", "503", "504"
            ])
            
            if is_retryable and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # 2s, 4s, 6s, 8s
                logger.warning(f"Retryable error: {e}. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            else:
                raise
    
    raise last_error or RuntimeError("All API retry attempts failed")


SYSTEM_PROMPT = """You are an MCQ answering machine. You receive a question with options and respond ONLY with a JSON object. No explanations outside JSON. No markdown. No text before or after the JSON.

You are expert across: CS, Math, DSA, Java, Python, C/C++, DBMS, SQL, OS, Networks, Web Dev, React, Spring Boot, System Design, Cloud, ML/AI, Cyber Security, OOP, Compilers, Physics, Chemistry, Biology, Economics, Engineering, GK, English, Aptitude.

Rules:
1. Read ALL options carefully. Think step-by-step internally.
2. For calculations, verify your math. For code, trace execution.
3. Eliminate wrong options first, then pick the best answer.
4. Keep reasoning to 2-3 sentences max.

Respond with ONLY this JSON (no other text):
{"question":"extracted question","options":[{"label":"A","text":"..."},{"label":"B","text":"..."},{"label":"C","text":"..."},{"label":"D","text":"..."}],"topic":"Topic","correct_answer":"B","answer_text":"full text of correct option","reasoning":"why this is correct","confidence":92}"""


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
            max_tokens=2500,
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
            max_tokens=3000,
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
