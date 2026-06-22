from dataclasses import dataclass, field
from typing import Any

RISK_THRESHOLDS = {
    "categories": {
        "Low": (0, 24),
        "Watchlist": (25, 49),
        "High Risk": (50, 74),
        "Critical": (75, 100),
    },
    "signals": {
        "dpd_current": {
            "description": "Current days past due on EMI",
            "bands": [
                {"min": 30, "points": 35, "label": "DPD >= 30 days"},
                {"min": 15, "points": 25, "label": "DPD 15-29 days"},
                {"min": 7, "points": 15, "label": "DPD 7-14 days"},
                {"min": 1, "points": 8, "label": "DPD 1-6 days"},
            ],
        },
        "dpd_trend": {
            "description": "Worsening late-payment trend over last 3 EMIs",
            "bands": [
                {"condition": "increasing_late_days", "points": 20, "label": "Late days increasing each cycle"},
                {"condition": "two_plus_late", "points": 12, "label": "2+ late payments in last 3 cycles"},
            ],
        },
        "failed_auto_debits": {
            "description": "Failed auto-debit attempts in last 60 days",
            "bands": [
                {"min_count": 3, "points": 20, "label": "3+ failed auto-debits"},
                {"min_count": 2, "points": 12, "label": "2 failed auto-debits"},
                {"min_count": 1, "points": 6, "label": "1 failed auto-debit"},
            ],
        },
        "partial_payments": {
            "description": "Partial EMI payments in recent history",
            "bands": [
                {"min_count": 2, "points": 18, "label": "2+ partial payments"},
                {"min_count": 1, "points": 10, "label": "1 partial payment"},
            ],
        },
        "utilization_rise": {
            "description": "Credit line utilization increase",
            "bands": [
                {"min_pct": 85, "points": 15, "label": "Utilization >= 85%"},
                {"min_rise_pct": 20, "points": 12, "label": "Utilization rose 20+ pts in 3 months"},
                {"min_pct": 70, "points": 8, "label": "Utilization >= 70%"},
            ],
        },
        "income_decline": {
            "description": "Declining salary/income inflows",
            "bands": [
                {"min_decline_pct": 30, "points": 15, "label": "Income down 30%+ vs 3-mo avg"},
                {"min_decline_pct": 15, "points": 8, "label": "Income down 15-29%"},
            ],
        },
        "insufficient_history": {
            "description": "Penalty when payment history is too short for reliable scoring",
            "bands": [{"max_payments": 2, "points": 5, "label": "Insufficient payment history (<3 EMIs)"}],
        },
    },
    "actions": {
        "Low": ["Continue standard monitoring"],
        "Watchlist": ["Soft reminder via SMS/email", "Monitor cash-flow signals weekly"],
        "High Risk": [
            "Proactive call within 48 hours",
            "Payment plan offer",
            "Manual analyst review",
        ],
        "Critical": [
            "Immediate proactive call",
            "Restructuring review",
            "Escalate to senior collections",
            "Manual analyst review",
        ],
    },
}


@dataclass
class RiskSignal:
    signal_id: str
    label: str
    points: int
    severity: str
    detail: str


@dataclass
class RiskAssessment:
    borrower_id: str
    borrower_name: str
    risk_score: int
    risk_category: str
    signals: list[RiskSignal] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    data_gaps: list[str] = field(default_factory=list)
    risk_trend: list[dict] = field(default_factory=list)


def _category_from_score(score: int) -> str:
    for cat, (lo, hi) in RISK_THRESHOLDS["categories"].items():
        if lo <= score <= hi:
            return cat
    return "Critical" if score > 74 else "Low"


def _severity(points: int) -> str:
    if points >= 20:
        return "high"
    if points >= 10:
        return "medium"
    return "low"


def _score_dpd(current_dpd: int) -> list[RiskSignal]:
    signals = []
    for band in RISK_THRESHOLDS["signals"]["dpd_current"]["bands"]:
        if current_dpd >= band["min"]:
            signals.append(
                RiskSignal(
                    signal_id="dpd_current",
                    label=band["label"],
                    points=band["points"],
                    severity=_severity(band["points"]),
                    detail=f"Current DPD: {current_dpd} days",
                )
            )
            break
    return signals


def _score_dpd_trend(history: list[dict]) -> list[RiskSignal]:
    signals = []
    recent = history[-3:] if len(history) >= 3 else history
    late_days = [p.get("days_late", 0) for p in recent if p.get("status") in ("late", "unpaid", "partial")]

    if len(late_days) >= 2 and all(late_days[i] <= late_days[i + 1] for i in range(len(late_days) - 1)):
        band = RISK_THRESHOLDS["signals"]["dpd_trend"]["bands"][0]
        signals.append(
            RiskSignal(
                signal_id="dpd_trend",
                label=band["label"],
                points=band["points"],
                severity=_severity(band["points"]),
                detail=f"Late days trend: {late_days}",
            )
        )
    elif sum(1 for p in recent if p.get("status") in ("late", "unpaid", "partial")) >= 2:
        band = RISK_THRESHOLDS["signals"]["dpd_trend"]["bands"][1]
        signals.append(
            RiskSignal(
                signal_id="dpd_trend",
                label=band["label"],
                points=band["points"],
                severity=_severity(band["points"]),
                detail=f"{sum(1 for p in recent if p.get('status') in ('late', 'unpaid', 'partial'))} problematic payments in last 3 cycles",
            )
        )
    return signals


def _score_auto_debits(attempts: list[dict]) -> list[RiskSignal]:
    failed = [a for a in attempts if a.get("status") == "failed"]
    signals = []
    for band in RISK_THRESHOLDS["signals"]["failed_auto_debits"]["bands"]:
        if len(failed) >= band["min_count"]:
            signals.append(
                RiskSignal(
                    signal_id="failed_auto_debits",
                    label=band["label"],
                    points=band["points"],
                    severity=_severity(band["points"]),
                    detail=f"{len(failed)} failed auto-debit(s); latest reason: {failed[-1].get('reason', 'unknown')}",
                )
            )
            break
    return signals


def _score_partial(history: list[dict]) -> list[RiskSignal]:
    partials = [p for p in history if p.get("status") == "partial"]
    signals = []
    for band in RISK_THRESHOLDS["signals"]["partial_payments"]["bands"]:
        if len(partials) >= band["min_count"]:
            signals.append(
                RiskSignal(
                    signal_id="partial_payments",
                    label=band["label"],
                    points=band["points"],
                    severity=_severity(band["points"]),
                    detail=f"{len(partials)} partial payment(s) detected",
                )
            )
            break
    return signals


def _score_utilization(credit_line: dict) -> list[RiskSignal]:
    signals = []
    limit = credit_line.get("limit", 0)
    utilized = credit_line.get("utilized", 0)
    history = credit_line.get("utilization_history", [])
    if limit <= 0:
        return signals

    pct = (utilized / limit) * 100
    rise = 0
    if len(history) >= 2:
        rise = ((history[-1] - history[0]) / limit) * 100

    applied = set()
    for band in RISK_THRESHOLDS["signals"]["utilization_rise"]["bands"]:
        key = band.get("label")
        if key in applied:
            continue
        if "min_pct" in band and pct >= band["min_pct"]:
            signals.append(
                RiskSignal(
                    signal_id="utilization_rise",
                    label=band["label"],
                    points=band["points"],
                    severity=_severity(band["points"]),
                    detail=f"Credit utilization at {pct:.0f}% ({utilized}/{limit})",
                )
            )
            applied.add(key)
        elif "min_rise_pct" in band and rise >= band["min_rise_pct"]:
            signals.append(
                RiskSignal(
                    signal_id="utilization_rise",
                    label=band["label"],
                    points=band["points"],
                    severity=_severity(band["points"]),
                    detail=f"Utilization rose {rise:.0f} percentage points over 3 months",
                )
            )
            applied.add(key)
    return signals


def _score_income(transactions: list[dict]) -> list[RiskSignal]:
    signals = []
    income = sorted(
        [t for t in transactions if t.get("type") == "credit" and t.get("category") in ("salary", "freelance")],
        key=lambda x: x.get("date", ""),
        reverse=True,
    )
    if len(income) < 2:
        return signals

    recent = income[0]["amount"]
    older = [t["amount"] for t in income[1:4]]
    if not older:
        return signals
    avg_older = sum(older) / len(older)
    if avg_older <= 0:
        return signals

    decline_pct = ((avg_older - recent) / avg_older) * 100
    for band in RISK_THRESHOLDS["signals"]["income_decline"]["bands"]:
        if decline_pct >= band["min_decline_pct"]:
            signals.append(
                RiskSignal(
                    signal_id="income_decline",
                    label=band["label"],
                    points=band["points"],
                    severity=_severity(band["points"]),
                    detail=f"Recent income ₹{recent:,} vs 3-mo avg ₹{avg_older:,.0f} ({decline_pct:.0f}% decline)",
                )
            )
            break
    return signals


def _check_data_gaps(borrower: dict) -> list[str]:
    gaps = []
    history = borrower.get("payment_history", [])
    if len(history) < 3:
        gaps.append("Fewer than 3 EMI cycles on record — trend signals may be unreliable")
    if not borrower.get("transactions"):
        gaps.append("No transaction data — income decline signal skipped")
    if not borrower.get("auto_debit_attempts"):
        gaps.append("No auto-debit history — debit failure signal skipped")
    cl = borrower.get("credit_line", {})
    if not cl.get("utilization_history"):
        gaps.append("No utilization history — utilization trend signal limited")
    return gaps


def _compute_risk_trend(borrower: dict) -> list[dict]:
    """Simulate monthly risk score trend from payment history."""
    history = borrower.get("payment_history", [])
    trend = []
    for i, payment in enumerate(history):
        partial = dict(borrower)
        partial["payment_history"] = history[: i + 1]
        partial["current_dpd"] = payment.get("days_late", 0) if payment.get("status") != "on_time" else 0
        sub = assess_borrower(partial, include_trend=False)
        trend.append({"month": payment.get("month"), "risk_score": sub.risk_score, "category": sub.risk_category})
    return trend


def assess_borrower(borrower: dict, include_trend: bool = True) -> RiskAssessment:
    signals: list[RiskSignal] = []
    data_gaps = _check_data_gaps(borrower)

    signals.extend(_score_dpd(borrower.get("current_dpd", 0)))
    signals.extend(_score_dpd_trend(borrower.get("payment_history", [])))
    signals.extend(_score_auto_debits(borrower.get("auto_debit_attempts", [])))
    signals.extend(_score_partial(borrower.get("payment_history", [])))
    signals.extend(_score_utilization(borrower.get("credit_line", {})))
    signals.extend(_score_income(borrower.get("transactions", [])))

    if len(borrower.get("payment_history", [])) < 3:
        band = RISK_THRESHOLDS["signals"]["insufficient_history"]["bands"][0]
        signals.append(
            RiskSignal(
                signal_id="insufficient_history",
                label=band["label"],
                points=band["points"],
                severity="low",
                detail="Limited EMI history available",
            )
        )

    total = min(100, sum(s.points for s in signals))
    category = _category_from_score(total)
    actions = list(RISK_THRESHOLDS["actions"].get(category, []))

    return RiskAssessment(
        borrower_id=borrower["borrower_id"],
        borrower_name=borrower.get("name", ""),
        risk_score=total,
        risk_category=category,
        signals=signals,
        recommended_actions=actions,
        data_gaps=data_gaps,
        risk_trend=_compute_risk_trend(borrower) if include_trend else [],
    )


def simulate_missed_emi(borrower: dict) -> RiskAssessment:
    """Scenario: what if the next EMI is missed entirely."""
    simulated = dict(borrower)
    emi = borrower["loan"]["emi_amount"]
    simulated["current_dpd"] = borrower.get("current_dpd", 0) + 30
    simulated["payment_history"] = list(borrower.get("payment_history", [])) + [
        {
            "month": "2025-07",
            "due_date": "2025-07-01",
            "paid_date": None,
            "amount_due": emi,
            "amount_paid": 0,
            "status": "unpaid",
            "days_late": simulated["current_dpd"],
        }
    ]
    simulated["auto_debit_attempts"] = list(borrower.get("auto_debit_attempts", [])) + [
        {"date": "2025-07-01", "status": "failed", "amount": emi, "reason": "insufficient_funds"}
    ]
    result = assess_borrower(simulated)
    result.signals.insert(
        0,
        RiskSignal(
            signal_id="scenario",
            label="Simulated: next EMI missed",
            points=0,
            severity="medium",
            detail="Hypothetical scenario — score reflects additional 30-day DPD and failed debit",
        ),
    )
    return result


def assessment_to_dict(assessment: RiskAssessment) -> dict[str, Any]:
    return {
        "borrower_id": assessment.borrower_id,
        "borrower_name": assessment.borrower_name,
        "risk_score": assessment.risk_score,
        "risk_category": assessment.risk_category,
        "signals": [
            {"signal_id": s.signal_id, "label": s.label, "points": s.points, "severity": s.severity, "detail": s.detail}
            for s in assessment.signals
        ],
        "recommended_actions": assessment.recommended_actions,
        "data_gaps": assessment.data_gaps,
        "risk_trend": assessment.risk_trend,
    }
