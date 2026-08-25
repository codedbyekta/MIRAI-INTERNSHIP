"""
Thin wrapper around the NEW unified Google GenAI SDK (google-genai package).
IMPORTANT: uses `from google import genai`, NOT the deprecated `google.generativeai`.

Responsibilities:
1. Question generation (text)
2. Audio transcription + understanding (audio -> text)
3. Persona-based evaluation (text) -- Technical persona also returns a follow-up
4. Camera frame -> confidence/posture note (vision, optional enrichment)
"""

import json
from google import genai

MODEL_NAME = "gemini-3.6-flash"  # keep configurable; verify against your API key's available models

_client = None


def configure_gemini(api_key: str):
    global _client
    _client = genai.Client(api_key=api_key)


def _get_client() -> genai.Client:
    if _client is None:
        raise RuntimeError("Gemini client not configured. Call configure_gemini(api_key) first.")
    return _client


def _clean_json(text: str) -> str:
    """Strip markdown fences if the model adds them despite instructions."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def generate_questions(prompt: str) -> list[str]:
    client = _get_client()
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    raw = _clean_json(response.text)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return [line.strip("-• ") for line in raw.split("\n") if line.strip()][:5]


def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """Send raw audio bytes to Gemini and get back a transcription."""
    client = _get_client()
    from google.genai import types
    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            audio_part,
            "Transcribe this audio verbatim. Return only the transcribed text, nothing else.",
        ],
    )
    return response.text.strip()


def analyze_posture(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Optional: give a one-line confidence/posture observation from the camera frame."""
    client = _get_client()
    from google.genai import types
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            image_part,
            "In one short sentence, comment on this person's visible posture/confidence "
            "for an interview setting. Be constructive, not judgmental.",
        ],
    )
    return response.text.strip()


def evaluate_answer(prompt: str) -> dict:
    """Generic persona evaluation (HR / Mentor). Returns score/strengths/gaps/feedback."""
    client = _get_client()
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    raw = _clean_json(response.text)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "score": 5,
            "strengths": "Could not parse structured feedback.",
            "gaps": "Model output was not valid JSON.",
            "feedback": raw[:300],
        }


def evaluate_technical_with_followup(prompt: str) -> dict:
    """
    Technical persona evaluation that ALSO decides whether an adaptive follow-up
    question is warranted, and if so, generates it.
    Returns: score/strengths/gaps/feedback/follow_up_needed/next_question
    """
    client = _get_client()
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    raw = _clean_json(response.text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "score": 5,
            "strengths": "Could not parse structured feedback.",
            "gaps": "Model output was not valid JSON.",
            "feedback": raw[:300],
            "follow_up_needed": False,
            "next_question": "",
        }
    data.setdefault("follow_up_needed", False)
    data.setdefault("next_question", "")
    return data
