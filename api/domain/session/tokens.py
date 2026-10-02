from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt

from api.contract_models import Role

SESSION_TTL = timedelta(minutes=15)
JWT_ALGORITHM = "HS256"
CUSTOMER: Role = "customer"
CONSULTANT: Role = "consultant"


@dataclass(frozen=True)
class SessionClaims:
    sub: str
    role: Role


def issue_token(secret: str, claims: SessionClaims, now: datetime) -> str:
    payload = {"sub": claims.sub, "role": claims.role, "iat": now, "exp": now + SESSION_TTL}
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def read_token(secret: str, token: str) -> SessionClaims | None:
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub", "role"]})
    except jwt.PyJWTError:
        return None
    role = payload["role"]
    if role == CUSTOMER:
        return SessionClaims(sub=str(payload["sub"]), role=CUSTOMER)
    if role == CONSULTANT:
        return SessionClaims(sub=str(payload["sub"]), role=CONSULTANT)
    return None
