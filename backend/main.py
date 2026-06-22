import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from auth.rbac import UserContext, authenticate, filter_borrowers, mask_borrower_for_role
from engine.risk_scorer import RISK_THRESHOLDS, assess_borrower, assessment_to_dict, simulate_missed_emi
from services.llm_service import generate_explanation

load_dotenv(Path(__file__).parent.parent / ".env")

app = FastAPI(
    title="Loan Default Risk Early Warning System",
    description="Proactive delinquency detection with explainable AI alerts",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).parent / "data" / "borrowers.json"
_sessions: dict[str, UserContext] = {}


def load_borrowers() -> list[dict]:
    with open(DATA_PATH) as f:
        return json.load(f)["borrowers"]


def get_current_user(authorization: Optional[str] = Header(None)) -> UserContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    token = authorization[7:]
    user = _sessions.get(token)
    if not user:
        raise HTTPException(401, "Invalid or expired session token")
    return user


class LoginRequest(BaseModel):
    username: str
    password: str


class QueryRequest(BaseModel):
    question: str


@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = authenticate(req.username, req.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    import secrets

    token = secrets.token_hex(16)
    _sessions[token] = user
    return {
        "token": token,
        "user": {
            "username": user.username,
            "role": user.role,
            "name": user.name,
            "borrower_id": user.borrower_id,
        },
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_configured": bool(os.getenv("LLM_API_TOKEN"))}


@app.get("/api/risk/thresholds")
def get_thresholds():
    return RISK_THRESHOLDS


@app.get("/api/borrowers")
async def list_borrowers(user: UserContext = Depends(get_current_user)):
    borrowers = load_borrowers()
    visible = filter_borrowers(user, borrowers)
    results = []
    for b in visible:
        assessment = assessment_to_dict(assess_borrower(b))
        masked = mask_borrower_for_role(user, b, assessment)
        results.append(
            {
                **masked,
                "assigned_analyst": b.get("assigned_analyst"),
                "loan_summary": {
                    "emi_amount": b["loan"]["emi_amount"],
                    "outstanding_balance": b["loan"]["outstanding_balance"],
                    "current_dpd": b.get("current_dpd", 0),
                },
            }
        )
    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return {"borrowers": results, "count": len(results)}


@app.get("/api/borrowers/{borrower_id}")
async def get_borrower(borrower_id: str, user: UserContext = Depends(get_current_user)):
    borrowers = load_borrowers()
    borrower = next((b for b in borrowers if b["borrower_id"] == borrower_id), None)
    if not borrower:
        raise HTTPException(404, "Borrower not found")
    if not filter_borrowers(user, [borrower]):
        raise HTTPException(403, "Access denied to this borrower")
    assessment = assessment_to_dict(assess_borrower(borrower))
    explanation = await generate_explanation(borrower, assessment)
    return {
        "borrower": {
            "borrower_id": borrower["borrower_id"],
            "name": borrower["name"],
            "loan": borrower["loan"],
            "current_dpd": borrower.get("current_dpd", 0),
            "payment_history": borrower.get("payment_history", []),
            "credit_line": borrower.get("credit_line", {}),
        },
        "assessment": mask_borrower_for_role(user, borrower, assessment),
        "alert": {
            "severity": assessment["risk_category"],
            "explanation": explanation["explanation"],
            "explanation_source": explanation["source"],
        },
    }


@app.post("/api/borrowers/{borrower_id}/query")
async def query_borrower(borrower_id: str, req: QueryRequest, user: UserContext = Depends(get_current_user)):
    if user.role == "borrower":
        raise HTTPException(403, "Borrowers cannot run analyst queries")
    borrowers = load_borrowers()
    borrower = next((b for b in borrowers if b["borrower_id"] == borrower_id), None)
    if not borrower:
        raise HTTPException(404, "Borrower not found")
    if not filter_borrowers(user, [borrower]):
        raise HTTPException(403, "Access denied")
    assessment = assessment_to_dict(assess_borrower(borrower))
    result = await generate_explanation(borrower, assessment, query=req.question)
    return {
        "borrower_id": borrower_id,
        "question": req.question,
        "answer": result["explanation"],
        "source": result["source"],
        "grounded_signals": assessment["signals"],
    }


@app.get("/api/borrowers/{borrower_id}/scenario/missed-emi")
def scenario_missed_emi(borrower_id: str, user: UserContext = Depends(get_current_user)):
    if user.role == "borrower":
        raise HTTPException(403, "Scenario simulation restricted to analysts/managers")
    borrowers = load_borrowers()
    borrower = next((b for b in borrowers if b["borrower_id"] == borrower_id), None)
    if not borrower:
        raise HTTPException(404, "Borrower not found")
    if not filter_borrowers(user, [borrower]):
        raise HTTPException(403, "Access denied")
    current = assessment_to_dict(assess_borrower(borrower))
    simulated = assessment_to_dict(simulate_missed_emi(borrower))
    return {
        "borrower_id": borrower_id,
        "current": current,
        "simulated_missed_emi": simulated,
        "score_delta": simulated["risk_score"] - current["risk_score"],
        "category_change": f"{current['risk_category']} → {simulated['risk_category']}",
    }


@app.get("/api/portfolio/summary")
def portfolio_summary(user: UserContext = Depends(get_current_user)):
    if user.role not in ("manager", "analyst"):
        raise HTTPException(403, "Portfolio summary requires manager or analyst role")
    borrowers = load_borrowers()
    visible = filter_borrowers(user, borrowers) if user.role == "analyst" else borrowers
    assessments = [assessment_to_dict(assess_borrower(b)) for b in visible]
    by_category: dict[str, int] = {"Low": 0, "Watchlist": 0, "High Risk": 0, "Critical": 0}
    total_exposure = 0
    for a, b in zip(assessments, visible):
        by_category[a["risk_category"]] = by_category.get(a["risk_category"], 0) + 1
        total_exposure += b["loan"]["outstanding_balance"]
    at_risk = by_category.get("High Risk", 0) + by_category.get("Critical", 0)
    return {
        "total_borrowers": len(assessments),
        "by_risk_category": by_category,
        "at_risk_count": at_risk,
        "at_risk_pct": round((at_risk / len(assessments) * 100) if assessments else 0, 1),
        "total_outstanding_exposure": total_exposure,
        "avg_risk_score": round(sum(a["risk_score"] for a in assessments) / len(assessments), 1) if assessments else 0,
    }
