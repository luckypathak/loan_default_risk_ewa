from dataclasses import dataclass
from typing import Optional

USERS = {
    "analyst1": {"password": "analyst1", "role": "analyst", "name": "Analyst One"},
    "analyst2": {"password": "analyst2", "role": "analyst", "name": "Analyst Two"},
    "manager1": {"password": "manager1", "role": "manager", "name": "Portfolio Manager"},
    "B101": {"password": "borrower", "role": "borrower", "name": "Priya Sharma", "borrower_id": "B101"},
    "B102": {"password": "borrower", "role": "borrower", "name": "Rahul Verma", "borrower_id": "B102"},
}


@dataclass
class UserContext:
    username: str
    role: str
    name: str
    borrower_id: Optional[str] = None


def authenticate(username: str, password: str) -> Optional[UserContext]:
    user = USERS.get(username)
    if not user or user["password"] != password:
        return None
    return UserContext(
        username=username,
        role=user["role"],
        name=user["name"],
        borrower_id=user.get("borrower_id"),
    )


def can_view_borrower(user: UserContext, borrower: dict) -> bool:
    if user.role == "manager":
        return True
    if user.role == "borrower":
        return borrower.get("borrower_id") == user.borrower_id
    if user.role == "analyst":
        return borrower.get("assigned_analyst") == user.username
    return False


def filter_borrowers(user: UserContext, borrowers: list[dict]) -> list[dict]:
    return [b for b in borrowers if can_view_borrower(user, b)]


def mask_borrower_for_role(user: UserContext, borrower: dict, assessment: dict) -> dict:
    """Strip sensitive fields based on role."""
    if user.role == "borrower":
        return {
            "borrower_id": assessment["borrower_id"],
            "borrower_name": assessment["borrower_name"],
            "risk_score": assessment["risk_score"],
            "risk_category": assessment["risk_category"],
            "signals": assessment["signals"],
            "recommended_actions": [a for a in assessment["recommended_actions"] if "collections" not in a.lower()],
            "data_gaps": assessment.get("data_gaps", []),
        }
    return assessment
