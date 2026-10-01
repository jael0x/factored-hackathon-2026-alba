import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections.abc import Callable
from typing import Annotated, get_args
from uuid import UUID

import jwt
import psycopg
from fastapi import Depends, Header

from api import agents, customers
from api.contract_models import Role
from api.errors import forbidden, unauthorized
from api.settings import settings

CODE_TTL = timedelta(seconds=600)
SESSION_TTL = timedelta(minutes=15)
MAX_WRONG_CODES = 5
CODE_DIGITS = 6
JWT_ALGORITHM = "HS256"
CUSTOMER: Role = "customer"
AGENT: Role = "agent"
ROLES: frozenset[str] = frozenset(get_args(Role))
BEARER_PREFIX = "Bearer "


@dataclass(frozen=True)
class IssuedCode:
    id: UUID
    code_hash: str
    expires_at: datetime
    wrong_codes: int
    used_at: datetime | None


@dataclass(frozen=True)
class CodeDelivery:
    email: str
    code: str


@dataclass(frozen=True)
class SessionClaims:
    sub: str
    role: Role


def new_code() -> str:
    return f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"


def hash_code(secret: str, subject_id: str, code: str) -> str:
    return hmac.new(secret.encode(), f"{subject_id}:{code}".encode(), hashlib.sha256).hexdigest()


def code_is_open(issued: IssuedCode, now: datetime) -> bool:
    return issued.used_at is None and now < issued.expires_at and issued.wrong_codes < MAX_WRONG_CODES


def code_matches(secret: str, subject_id: str, issued: IssuedCode, code: str) -> bool:
    return hmac.compare_digest(issued.code_hash, hash_code(secret, subject_id, code))


def issue_token(secret: str, claims: SessionClaims, now: datetime) -> str:
    payload = {"sub": claims.sub, "role": claims.role, "iat": now, "exp": now + SESSION_TTL}
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def read_token(secret: str, token: str) -> SessionClaims | None:
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub", "role"]})
    except jwt.PyJWTError:
        return None
    role = payload["role"]
    if role not in ROLES:
        return None
    return SessionClaims(sub=str(payload["sub"]), role=role)


def store_code(conn: psycopg.Connection, subject_id: str, role: Role, code_hash: str, now: datetime) -> None:
    conn.execute(
        "INSERT INTO login_codes (subject_id, role, code_hash, expires_at, created_at) VALUES (%s, %s, %s, %s, %s)",
        (subject_id, role, code_hash, now + CODE_TTL, now),
    )


def latest_code(conn: psycopg.Connection, subject_id: str, role: Role) -> IssuedCode | None:
    row = conn.execute(
        """
        SELECT id, code_hash, expires_at, wrong_codes, used_at
        FROM login_codes
        WHERE subject_id = %s AND role = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (subject_id, role),
    ).fetchone()
    return IssuedCode(*row) if row else None


def record_wrong_code(conn: psycopg.Connection, code_id: UUID) -> None:
    conn.execute("UPDATE login_codes SET wrong_codes = wrong_codes + 1 WHERE id = %s", (code_id,))


def spend_code(conn: psycopg.Connection, code_id: UUID, now: datetime) -> bool:
    row = conn.execute(
        "UPDATE login_codes SET used_at = %s WHERE id = %s AND used_at IS NULL RETURNING id",
        (now, code_id),
    ).fetchone()
    return row is not None


def issue_code(
    conn: psycopg.Connection, secret: str, subject_id: str, role: Role, email: str, now: datetime
) -> CodeDelivery:
    code = new_code()
    store_code(conn, subject_id, role, hash_code(secret, subject_id, code), now)
    return CodeDelivery(email=email, code=code)


def redeem_code(
    conn: psycopg.Connection, secret: str, subject_id: str, role: Role, code: str, now: datetime
) -> bool:
    issued = latest_code(conn, subject_id, role)
    if issued is None or not code_is_open(issued, now):
        return False
    if not code_matches(secret, subject_id, issued, code):
        record_wrong_code(conn, issued.id)
        return False
    return spend_code(conn, issued.id, now)


def issue_customer_code(conn: psycopg.Connection, secret: str, document_number: str, now: datetime) -> CodeDelivery | None:
    customer = customers.find_by_document(conn, document_number)
    if customer is None or customer.email is None:
        return None
    return issue_code(conn, secret, customer.customer_id, CUSTOMER, customer.email, now)


def open_customer_session(
    conn: psycopg.Connection, secret: str, document_number: str, code: str, now: datetime
) -> SessionClaims | None:
    customer = customers.find_by_document(conn, document_number)
    if customer is None or not redeem_code(conn, secret, customer.customer_id, CUSTOMER, code, now):
        return None
    return SessionClaims(sub=customer.customer_id, role=CUSTOMER)


def issue_agent_code(
    conn: psycopg.Connection, secret: str, email: str, employee_code: str, now: datetime
) -> CodeDelivery | None:
    agent = agents.find_active_by_login(conn, email, employee_code)
    if agent is None:
        return None
    return issue_code(conn, secret, agent.agent_id, AGENT, agent.email, now)


def open_agent_session(
    conn: psycopg.Connection, secret: str, email: str, employee_code: str, code: str, now: datetime
) -> SessionClaims | None:
    agent = agents.find_active_by_login(conn, email, employee_code)
    if agent is None or not redeem_code(conn, secret, agent.agent_id, AGENT, code, now):
        return None
    return SessionClaims(sub=agent.agent_id, role=AGENT)


def get_session(authorization: Annotated[str | None, Header()] = None) -> SessionClaims:
    if authorization is None or not authorization.startswith(BEARER_PREFIX):
        raise unauthorized()
    claims = read_token(settings.jwt_secret, authorization.removeprefix(BEARER_PREFIX))
    if claims is None:
        raise unauthorized()
    return claims


def require_role(role: Role) -> Callable[[SessionClaims], SessionClaims]:
    def check(session: Annotated[SessionClaims, Depends(get_session)]) -> SessionClaims:
        if session.role != role:
            raise forbidden()
        return session

    return check


require_customer = require_role(CUSTOMER)
require_agent = require_role(AGENT)
