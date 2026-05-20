"""
Question / MCQ parser — Extracts structured question data from raw OCR text.

Identifies the question stem, option labels (A/B/C/D or 1/2/3/4),
and option text using regex heuristics.
"""

import re
from app.models import MCQOption


# Patterns for option labels
OPTION_PATTERNS = [
    # A) or A. or (A) style
    re.compile(
        r"^\s*(?:\(?([A-Da-d])\)?[\.\)\:])\s*(.+)$", re.MULTILINE
    ),
    # 1) or 1. style
    re.compile(
        r"^\s*(?:\(?([1-4])\)?[\.\)\:])\s*(.+)$", re.MULTILINE
    ),
    # a) lowercase
    re.compile(
        r"^\s*([a-d])\)\s*(.+)$", re.MULTILINE
    ),
]

# Common question number prefixes to strip
Q_NUM_PATTERN = re.compile(
    r"^\s*(?:Q(?:uestion)?\.?\s*\d+[\.\)\:]\s*|"
    r"\d+[\.\)]\s*)",
    re.IGNORECASE,
)


def parse_question_text(raw_text: str) -> dict:
    """
    Parse raw OCR text into a structured question dict.

    Returns:
        {
            "question": str,
            "options": [{"label": "A", "text": "..."}, ...],
            "raw_text": str
        }
    """
    if not raw_text or not raw_text.strip():
        return {"question": "", "options": [], "raw_text": raw_text}

    options: list[MCQOption] = []
    option_spans = []

    # Try each pattern
    for pattern in OPTION_PATTERNS:
        matches = list(pattern.finditer(raw_text))
        if len(matches) >= 2:  # Need at least 2 options to be valid
            for m in matches:
                label = m.group(1).upper()
                text = m.group(2).strip()
                options.append(MCQOption(label=label, text=text))
                option_spans.append((m.start(), m.end()))
            break

    # Normalize labels to A/B/C/D if they were numeric
    label_map = {"1": "A", "2": "B", "3": "C", "4": "D"}
    for opt in options:
        if opt.label in label_map:
            opt.label = label_map[opt.label]

    # Extract question text (everything before the first option)
    if option_spans:
        question_text = raw_text[: option_spans[0][0]].strip()
    else:
        question_text = raw_text.strip()

    # Strip question number prefix
    question_text = Q_NUM_PATTERN.sub("", question_text).strip()

    return {
        "question": question_text,
        "options": [o.model_dump() for o in options],
        "raw_text": raw_text,
    }
