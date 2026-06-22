import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

LLM_URL = os.getenv("LLM_WRAPPER_URL", "https://llm-wrapper-741152993481.asia-south1.run.app/llm/query")
LLM_TOKEN = os.getenv("LLM_API_TOKEN", "")


def _build_grounded_context(borrower: dict, assessment: dict) -> str:
    return json.dumps(
        {
            "borrower_id": assessment["borrower_id"],
            "borrower_name": assessment["borrower_name"],
            "risk_score": assessment["risk_score"],
            "risk_category": assessment["risk_category"],
            "loan": {
                "emi_amount": borrower["loan"]["emi_amount"],
                "outstanding_balance": borrower["loan"]["outstanding_balance"],
                "current_dpd": borrower.get("current_dpd", 0),
            },
            "triggered_signals": assessment["signals"],
            "recommended_actions": assessment["recommended_actions"],
            "data_gaps": assessment.get("data_gaps", []),
        },
        indent=2,
    )


def _template_explanation(assessment: dict) -> str:
    signals = assessment.get("signals", [])
    top = sorted(signals, key=lambda s: s.get("points", 0), reverse=True)[:3]
    reasons = "; ".join(s["label"] for s in top) or "No significant risk signals"
    actions = ", ".join(assessment.get("recommended_actions", [])[:2])
    return (
        f"Borrower {assessment['borrower_id']} is rated {assessment['risk_category']} "
        f"(score {assessment['risk_score']}/100). Primary drivers: {reasons}. "
        f"Recommended: {actions}."
    )


def _build_prompt(context: str, query: str | None = None) -> str:
    base = f"""You are a credit risk analyst assistant for a lending platform.
Answer ONLY using the JSON data below. Do not invent numbers, dates, or events.
If data is missing, say so explicitly. Keep response under 150 words, professional tone.

BORROWER RISK DATA:
{context}
"""
    if query:
        return base + f"\nANALYST QUESTION: {query}\n\nProvide a grounded answer citing specific signals from the data."
    return base + "\nWrite a concise alert explanation for the collections team: why flagged, severity, and top 2 recommended actions."


async def generate_explanation(
    borrower: dict,
    assessment: dict,
    query: str | None = None,
) -> dict[str, Any]:
    context = _build_grounded_context(borrower, assessment)
    prompt = _build_prompt(context, query)
    fallback = _template_explanation(assessment)

    if not LLM_TOKEN:
        return {
            "explanation": fallback,
            "source": "template_fallback",
            "grounded_context_hash": hash(context) % 10**8,
            "note": "LLM_API_TOKEN not set — using template",
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                LLM_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {LLM_TOKEN}",
                },
                json={
                    "prompt": prompt,
                    "metadata": {
                        "client": "loan-default-ewa",
                        "borrower_id": assessment["borrower_id"],
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = (
                data.get("response")
                or data.get("text")
                or data.get("content")
                or data.get("answer")
                or (data.get("choices", [{}])[0].get("message", {}).get("content") if isinstance(data.get("choices"), list) else None)
            )
            if text is None:
                text = str(data)
            if isinstance(text, dict):
                text = text.get("content", fallback)
            text = str(text).strip()
            if not text or len(text) < 20:
                text = fallback
                source = "template_fallback"
            else:
                source = "llm_generated"
            return {
                "explanation": text,
                "source": source,
                "grounded_context_hash": hash(context) % 10**8,
            }
    except Exception as exc:
        return {
            "explanation": fallback,
            "source": "template_fallback",
            "grounded_context_hash": hash(context) % 10**8,
            "error": str(exc),
        }
