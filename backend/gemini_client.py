"""gemini_client.py — Gemini 2.0 Flash code analysis"""
import os, json, asyncio
from google import genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """You are CodeLens, a senior security engineer and code reviewer.
Analyse the provided code for: security vulnerabilities (OWASP Top-10, CWE),
code quality issues, performance problems, and style/best-practice violations.
Be thorough. Return ONLY a valid JSON object — no markdown, no extra text."""

RESPONSE_SCHEMA = """{
  "score": <integer 0-100 — higher means safer/better>,
  "summary": "<one sentence overview of the code health>",
  "findings": [
    {
      "severity": "<critical|high|medium|low|info>",
      "category": "<security|quality|performance|style>",
      "title": "<short title, max 60 chars>",
      "line_start": <integer or null>,
      "line_end": <integer or null>,
      "description": "<clear explanation of the issue>",
      "fix": "<concrete fix suggestion>",
      "references": ["<CWE-xxx or OWASP Axx — optional>"]
    }
  ]
}"""

async def analyze_code(code: str, language: str) -> dict:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in .env")

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""{SYSTEM_PROMPT}

Language: {language}

Code to review:
```{language}
{code}
```

Return ONLY this JSON structure (no markdown fences):
{RESPONSE_SCHEMA}"""

    # Run in thread pool with fast primary model + fallback
    from google.genai import types
    loop = asyncio.get_event_loop()
    models_to_try = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
    last_err = None
    response = None

    for model_name in models_to_try:
        try:
            response = await loop.run_in_executor(
                None,
                lambda m=model_name: client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        http_options=types.HttpOptions(timeout=20000)
                    ),
                )
            )
            break
        except Exception as e:
            last_err = e
            msg = str(e)
            if any(code in msg for code in ("503", "UNAVAILABLE", "429", "404", "NOT_FOUND", "timed out")):
                continue
            raise

    if response is None:
        raise last_err

    raw = response.text.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)
    # Ensure required keys exist
    result.setdefault("score", 50)
    result.setdefault("summary", "Review complete.")
    result.setdefault("findings", [])
    return result
