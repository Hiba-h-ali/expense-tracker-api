import json
import os
from collections.abc import Sequence
from urllib import error, parse, request


def _extract_category(text: str) -> str | None:
    cleaned = text.strip()
    if not cleaned:
        return None

    try:
        parsed = json.loads(cleaned)
        category = parsed.get("category")
        if isinstance(category, str) and category.strip():
            return category.strip().lower()
    except json.JSONDecodeError:
        pass

    return cleaned.splitlines()[0].strip().strip('"').lower() or None


def categorize_expense(description: str, allowed_categories: Sequence[str]) -> str:
    """Categorize an expense using Gemini. Returns a category name."""
    normalized_allowed = [
        category.strip().lower()
        for category in allowed_categories
        if category and category.strip()
    ]
    if not normalized_allowed:
        return "uncategorized"

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "uncategorized"

    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    base_url = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta")
    endpoint = f"{base_url}/models/{model}:generateContent?key={parse.quote(api_key)}"

    prompt = (
        "You are an expense categorization assistant.\n"
        "Pick exactly one category from this allowed list and return JSON only.\n"
        f"Allowed categories: {', '.join(normalized_allowed)}\n"
        f"Expense description: {description}\n"
        'Return exactly: {"category":"<one allowed category>"}'
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }

    try:
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=6) as response:
            response_json = json.loads(response.read().decode("utf-8"))
        text = response_json["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, json.JSONDecodeError, error.URLError, TimeoutError):
        return "uncategorized"

    category = _extract_category(text)
    if category in normalized_allowed:
        return category
    return "uncategorized"