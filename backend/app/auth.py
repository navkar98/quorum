"""Demo-grade role-based auth.

Tokens are simple opaque strings mapped to a seeded app_user. In a real system these
would be real credentials; for the hackathon they establish role + actor identity so
server-side authorization can be enforced and tested.

Token format: "quorum-<user_id>". The user's role and device_id come from the DB.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from .db import get_conn


@dataclass
class Principal:
    user_id: int
    role: str
    display_name: str
    device_id: str | None

    @property
    def is_security(self) -> bool:
        return self.role == "security"


def _parse_token(authorization: str | None) -> int:
    if not authorization:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if not token.startswith("quorum-"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    try:
        return int(token.split("-", 1)[1])
    except (IndexError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed token")


def get_principal(authorization: str | None = Header(default=None)) -> Principal:
    user_id = _parse_token(authorization)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, role, display_name, device_id FROM app_user WHERE id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return Principal(row["id"], row["role"], row["display_name"], row["device_id"])


def require_security(principal: Principal = Depends(get_principal)) -> Principal:
    """Guard for privileged, security-only operations. Enforced server-side."""
    if not principal.is_security:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This operation requires a security role",
        )
    return principal


def require_student(principal: Principal = Depends(get_principal)) -> Principal:
    if principal.role != "student":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Student role required")
    return principal
