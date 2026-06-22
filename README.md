# Loan Default Risk Early Warning System

Proactive fintech lending prototype that flags borrowers likely to become delinquent within 30 days using rule-based risk scoring, explainable alerts, and LLM-grounded analyst Q&A.

## Quick start

### Backend
```bash
cd loan-default-ewa/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # add LLM_API_TOKEN
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd loan-default-ewa/frontend
npm install
npm run dev
```

Open **http://localhost:5174**

## Demo logins

| Role     | Username  | Password  | Access                          |
|----------|-----------|---------|----------------------------------|
| Analyst  | analyst1  | analyst1| Assigned borrowers (B101,B102,B105) |
| Analyst  | analyst2  | analyst2| Assigned borrowers (B103,B104,B106) |
| Manager  | manager1  | manager1| Full portfolio + summary         |
| Borrower | B101      | borrower| Own risk view only               |

## System flow

```
Mock JSON data → Risk Engine (rules) → Risk category + signals + actions
                                              ↓
                                    LLM explanation (grounded)
                                              ↓
                              Dashboard / API (RBAC-filtered)
```

1. **Ingest** — `backend/data/borrowers.json` holds loan, payment, transaction, and utilization data.
2. **Score** — `engine/risk_scorer.py` computes weighted signals and maps to Low / Watchlist / High Risk / Critical.
3. **Alert** — Each borrower gets signals, recommended actions, and an LLM explanation constrained to provided facts.
4. **Consume** — Analysts use dashboard + natural-language queries; borrowers see masked self-service view.

## Risk scoring (documented thresholds)

| Signal | Condition | Points |
|--------|-----------|--------|
| DPD current | 1–6 / 7–14 / 15–29 / 30+ days | 8 / 15 / 25 / 35 |
| DPD trend | 2+ late in last 3 cycles; increasing late days | 12 / 20 |
| Failed auto-debits | 1 / 2 / 3+ failures | 6 / 12 / 20 |
| Partial payments | 1 / 2+ partial EMIs | 10 / 18 |
| Utilization | ≥70% / ≥85% / +20pt rise | 8 / 15 / 12 |
| Income decline | 15–29% / 30%+ vs 3-mo avg | 8 / 15 |
| Insufficient history | &lt;3 EMI records | 5 |

**Categories:** Low (0–24) · Watchlist (25–49) · High Risk (50–74) · Critical (75–100)

Full config: `GET /api/risk/thresholds`

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Simulated auth, returns Bearer token |
| GET | `/api/borrowers` | List borrowers by risk (RBAC) |
| GET | `/api/borrowers/{id}` | Detail + LLM alert explanation |
| POST | `/api/borrowers/{id}/query` | Analyst Q&A (grounded) |
| GET | `/api/borrowers/{id}/scenario/missed-emi` | What-if simulation |
| GET | `/api/portfolio/summary` | Manager/analyst portfolio stats |
| GET | `/api/risk/thresholds` | Scoring documentation |

## LLM grounding safeguards

- Only structured JSON from the risk engine is sent to the model.
- Prompt explicitly forbids inventing facts not in context.
- Template fallback if API fails or token missing.
- Responses tagged `llm_generated` vs `template_fallback` for audit.

## Security & privacy (prototype vs production)

**Prototype:** In-memory session tokens; mock users in `auth/rbac.py`.

**Production would add:**
- OAuth2/JWT with short TTL and refresh rotation
- Row-level security: `borrower_id` and `assigned_analyst` enforced at DB query layer
- PII minimization in LLM prompts (no PAN/Aadhaar; aggregate where possible)
- Immutable audit log for alert views and explanation generation
- Encryption at rest for borrower financials; TLS in transit
- Role-based field masking (borrowers never see internal collection escalation notes)

## Sample data schema

```json
{
  "borrower_id": "B102",
  "name": "Rahul Verma",
  "assigned_analyst": "analyst1",
  "loan": { "emi_amount": 11200, "outstanding_balance": 245000 },
  "payment_history": [{ "month": "2025-06", "status": "unpaid", "days_late": 12 }],
  "auto_debit_attempts": [{ "status": "failed", "reason": "insufficient_funds" }],
  "transactions": [{ "type": "credit", "category": "salary", "amount": 38000 }],
  "credit_line": { "limit": 80000, "utilized": 62000, "utilization_history": [] },
  "current_dpd": 12
}
```

## Test scenarios

1. **B101 (Priya)** — All EMIs on time → expect **Low** risk.
2. **B102 (Rahul)** — Rising DPD, failed debits, income drop → **High Risk** or **Critical**.
3. **B104 (Vikram)** — Only 2 EMI records → insufficient history flag + elevated uncertainty.
4. **B105 (Meera)** — 33 DPD, partial payments, max utilization → **Critical**.
5. **Analyst query** — `Why was borrower B102 flagged?` → answer cites DPD, debits, income only.
6. **RBAC** — Login as `B101` → cannot see B102; cannot run analyst queries.
7. **Scenario** — Simulate missed EMI on B106 → score increases, category may upgrade.

## Assumptions & limitations

- Rule-based scoring, not ML — suitable for prototype; production would calibrate on historical roll rates.
- Mock static JSON — no real-time bank feeds or bureau data.
- DPD and dates are as-of assignment snapshot (June 2025).
- LLM adds narrative only; **decisions are driven by deterministic rules**.
- No model versioning, A/B testing, or feedback loop (would be needed in production).

## Bonus features included

- Risk trend visualization (monthly score bars on borrower detail)
- Scenario simulation (“What if next EMI is missed?”)
- Portfolio-level summary for managers

## Project structure

```
loan-default-ewa/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── auth/rbac.py         # Simulated RBAC
│   ├── engine/risk_scorer.py
│   ├── services/llm_service.py
│   └── data/borrowers.json
├── frontend/                # React dashboard
└── README.md
```
