from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from api.application.session.issue_code import issue_agent_code, issue_customer_code
from api.application.session.open_session import open_agent_session, open_customer_session
from api.domain.agents.identity import AgentIdentity
from api.domain.agents.login import AgentLoginKey
from api.domain.customers.identity import CustomerIdentity
from api.domain.session import codes
from api.domain.session.codes import IssuedCode
from api.domain.session.tokens import AGENT, CUSTOMER

SECRET = "unit-test-secret-0123456789abcdefghij"
NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
JUAN = CustomerIdentity("CLI-9EDEKZ8OUNUR", "Juan Alberto", "Romero González", "juan.romero@example.com")
NO_EMAIL = CustomerIdentity("CLI-MOCK00000000", "Rosa Elena", "Díaz Mora", None)
CESAR = AgentIdentity(
    "AGT-OJ9N4FGYV9", "E75612", "César", "González Sánchez", "cesar.gonzalez@example.com", "Active", "Créditos"
)
CESAR_KEY = AgentLoginKey("cesar.gonzalez@example.com", "E75612")


class MemCustomers:
    def __init__(self, rows: dict[str, CustomerIdentity]) -> None:
        self.rows = rows

    def find_by_document(self, document_number: str) -> CustomerIdentity | None:
        return self.rows.get(document_number)

    def find_by_id(self, customer_id: str) -> CustomerIdentity | None:
        for row in self.rows.values():
            if row.customer_id == customer_id:
                return row
        return None


class MemAgents:
    def __init__(self, rows: dict[AgentLoginKey, AgentIdentity]) -> None:
        self.rows = rows

    def find_by_login(self, key: AgentLoginKey) -> AgentIdentity | None:
        return self.rows.get(key)

    def find_by_id(self, agent_id: str) -> AgentIdentity | None:
        return next((row for row in self.rows.values() if row.agent_id == agent_id), None)


class MemCodes:
    def __init__(self, issued: IssuedCode | None = None, spend_result: bool = True) -> None:
        self.issued = issued
        self.spend_result = spend_result
        self.stored: list[str] = []
        self.subjects: list[tuple[str, str]] = []
        self.wrong: list[UUID] = []
        self.spent = False

    def store(self, subject_id: str, role: str, code_hash: str, now: datetime) -> None:
        self.stored.append(code_hash)
        self.subjects.append((subject_id, role))

    def latest(self, subject_id: str, role: str) -> IssuedCode | None:
        return self.issued

    def record_wrong(self, code_id: UUID) -> None:
        self.wrong.append(code_id)

    def spend(self, code_id: UUID, now: datetime) -> bool:
        self.spent = True
        return self.spend_result


def test_an_unknown_document_stores_nothing() -> None:
    login_codes = MemCodes()
    delivery = issue_customer_code(MemCustomers({}), login_codes, SECRET, "00000000", NOW)
    assert delivery is None
    assert login_codes.stored == []


def test_a_customer_without_email_stores_nothing() -> None:
    login_codes = MemCodes()
    delivery = issue_customer_code(MemCustomers({"52917380": NO_EMAIL}), login_codes, SECRET, "52917380", NOW)
    assert delivery is None
    assert login_codes.stored == []


def test_a_known_customer_stores_the_hash_of_the_code() -> None:
    login_codes = MemCodes()
    delivery = issue_customer_code(MemCustomers({"71034840": JUAN}), login_codes, SECRET, "71034840", NOW)
    assert delivery is not None
    assert delivery.email == JUAN.email
    assert login_codes.stored == [codes.hash_code(SECRET, JUAN.customer_id, delivery.code)]
    assert delivery.code not in login_codes.stored[0]


def test_a_wrong_code_is_counted_and_does_not_open_a_session() -> None:
    issued = IssuedCode(uuid4(), codes.hash_code(SECRET, JUAN.customer_id, "481206"), NOW + codes.CODE_TTL, 0, None)
    login_codes = MemCodes(issued)
    claims = open_customer_session(MemCustomers({"71034840": JUAN}), login_codes, SECRET, "71034840", "000000", NOW)
    assert claims is None
    assert login_codes.wrong == [issued.id]
    assert login_codes.spent is False


def test_the_right_code_is_spent_and_returns_the_customer() -> None:
    issued = IssuedCode(uuid4(), codes.hash_code(SECRET, JUAN.customer_id, "481206"), NOW + codes.CODE_TTL, 0, None)
    login_codes = MemCodes(issued)
    claims = open_customer_session(MemCustomers({"71034840": JUAN}), login_codes, SECRET, "71034840", "481206", NOW)
    assert claims is not None
    assert claims.sub == JUAN.customer_id
    assert claims.role == CUSTOMER
    assert login_codes.wrong == []
    assert login_codes.spent is True


def test_a_code_that_cannot_be_spent_does_not_open_a_session() -> None:
    issued = IssuedCode(uuid4(), codes.hash_code(SECRET, JUAN.customer_id, "481206"), NOW + codes.CODE_TTL, 0, None)
    login_codes = MemCodes(issued, spend_result=False)
    claims = open_customer_session(MemCustomers({"71034840": JUAN}), login_codes, SECRET, "71034840", "481206", NOW)
    assert claims is None
    assert login_codes.spent is True


def cesar_issued_code() -> IssuedCode:
    return IssuedCode(uuid4(), codes.hash_code(SECRET, CESAR.agent_id, "481206"), NOW + codes.CODE_TTL, 0, None)


def test_an_active_agent_stores_the_hash_of_the_code_under_the_agent_role() -> None:
    login_codes = MemCodes()
    delivery = issue_agent_code(MemAgents({CESAR_KEY: CESAR}), login_codes, SECRET, CESAR.email, "E75612", NOW)
    assert delivery is not None
    assert delivery.email == CESAR.email
    assert login_codes.stored == [codes.hash_code(SECRET, CESAR.agent_id, delivery.code)]
    assert login_codes.subjects == [(CESAR.agent_id, AGENT)]


def test_the_typed_pair_is_matched_trimmed_and_without_case() -> None:
    login_codes = MemCodes()
    agents = MemAgents({CESAR_KEY: CESAR})
    delivery = issue_agent_code(agents, login_codes, SECRET, "  Cesar.Gonzalez@EXAMPLE.com ", " e75612 ", NOW)
    assert delivery is not None
    assert login_codes.subjects == [(CESAR.agent_id, AGENT)]


@pytest.mark.parametrize("status", ["Vacation", "Leave", "Inactive"])
def test_an_agent_who_is_not_active_stores_nothing(status: str) -> None:
    login_codes = MemCodes()
    away = MemAgents({CESAR_KEY: replace(CESAR, agent_status=status)})
    assert issue_agent_code(away, login_codes, SECRET, CESAR.email, "E75612", NOW) is None
    assert login_codes.stored == []


def test_an_unknown_pair_stores_nothing() -> None:
    login_codes = MemCodes()
    assert issue_agent_code(MemAgents({CESAR_KEY: CESAR}), login_codes, SECRET, CESAR.email, "E30001", NOW) is None
    assert login_codes.stored == []


def test_the_right_agent_code_is_spent_and_returns_the_agent() -> None:
    issued = cesar_issued_code()
    login_codes = MemCodes(issued)
    claims = open_agent_session(MemAgents({CESAR_KEY: CESAR}), login_codes, SECRET, CESAR.email, "E75612", "481206", NOW)
    assert claims is not None
    assert claims.sub == CESAR.agent_id
    assert claims.role == AGENT
    assert login_codes.spent is True


def test_an_agent_who_is_no_longer_active_cannot_use_a_sent_code() -> None:
    login_codes = MemCodes(cesar_issued_code())
    on_leave = MemAgents({CESAR_KEY: replace(CESAR, agent_status="Leave")})
    assert open_agent_session(on_leave, login_codes, SECRET, CESAR.email, "E75612", "481206", NOW) is None
    assert login_codes.wrong == []
    assert login_codes.spent is False


def test_a_wrong_agent_code_is_counted_and_does_not_open_a_session() -> None:
    issued = cesar_issued_code()
    login_codes = MemCodes(issued)
    claims = open_agent_session(MemAgents({CESAR_KEY: CESAR}), login_codes, SECRET, CESAR.email, "E75612", "000000", NOW)
    assert claims is None
    assert login_codes.wrong == [issued.id]
    assert login_codes.spent is False
