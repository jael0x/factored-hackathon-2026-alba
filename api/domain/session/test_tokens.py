from datetime import UTC, datetime, timedelta
from typing import get_args

import jwt

from api.contract_models import Role as WireRole
from api.domain.session.tokens import AGENT, CUSTOMER, SESSION_TTL, Role, SessionClaims, issue_token, read_token

SECRET = "unit-test-secret-0123456789abcdefghij"
SUBJECT = "CLI-9EDEKZ8OUNUR"


def test_domain_role_matches_the_wire_role() -> None:
    assert set(get_args(Role)) == set(get_args(WireRole))


def test_every_domain_role_round_trips() -> None:
    now = datetime.now(UTC)
    for role in get_args(Role):
        claims = SessionClaims(sub=SUBJECT, role=role)
        assert read_token(SECRET, issue_token(SECRET, claims, now)) == claims


def test_token_expires_after_fifteen_minutes() -> None:
    claims = SessionClaims(sub=SUBJECT, role=CUSTOMER)
    token = issue_token(SECRET, claims, datetime.now(UTC) - SESSION_TTL - timedelta(seconds=1))
    assert read_token(SECRET, token) is None


def test_token_signed_with_another_secret_is_rejected() -> None:
    claims = SessionClaims(sub=SUBJECT, role=CUSTOMER)
    token = issue_token("another-secret-0123456789abcdefghijkl", claims, datetime.now(UTC))
    assert read_token(SECRET, token) is None


def test_token_with_an_unknown_role_is_rejected() -> None:
    token = jwt.encode(
        {"sub": SUBJECT, "role": "admin", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        SECRET,
        "HS256",
    )
    assert read_token(SECRET, token) is None


def test_an_agent_claim_is_not_a_customer_claim() -> None:
    claims = SessionClaims(sub="AGT-OJ9N4FGYV9", role=AGENT)
    assert read_token(SECRET, issue_token(SECRET, claims, datetime.now(UTC))) == claims
    assert claims.role != CUSTOMER
