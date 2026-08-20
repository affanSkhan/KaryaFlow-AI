from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/ai", tags=["ai"])


def gemini_text(prompt: str) -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800},
    }
    response = httpx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        params={"key": key},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


@router.get("/status")
def ai_status() -> dict[str, Any]:
    return {"configured": bool(os.getenv("GEMINI_API_KEY", "").strip()), "provider": "Gemini", "purpose": "explain verified exceptions and draft operational communications"}


@router.post("/draft")
def ai_draft(payload: dict[str, Any]) -> dict[str, str]:
    facts = payload.get("facts", "")
    fallback = payload.get("fallback", "Please review the verified procurement exception and contact the vendor for clarification.")
    prompt = f"""You are KaryaFlow AI, an operations copilot. Draft a concise, professional vendor clarification message using ONLY the verified facts below. Never invent quantities, dates, prices, causes, or policy. Mention the exact variance and ask one clear question. Do not mention AI.\n\nVerified facts:\n{facts}"""
    try:
        return {"draft": gemini_text(prompt), "mode": "gemini"}
    except Exception:
        return {"draft": fallback, "mode": "deterministic-fallback"}
