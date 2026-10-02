from dataclasses import dataclass, field

import psycopg
from fastapi.testclient import TestClient

from api.contract_models import Role

LOGIN_TEST_DB = "alba_api_test"


@dataclass(frozen=True)
class Customer:
    customer_id: str
    document_number: str
    first_name: str
    last_name: str
    email: str | None
    country: str


@dataclass(frozen=True)
class Consultant:
    consultant_id: str
    employee_code: str
    first_name: str
    last_name: str
    email: str
    status: str
    specialty: str | None


JUAN = Customer("CLI-9EDEKZ8OUNUR", "71034840", "Juan Alberto", "Romero González", "juan.romero@example.com", "México")
ALICIA = Customer("CLI-440CO5FZIY6A", "1144095213", "Alicia Mariana", "Parra Álvarez", "alicia.parra@example.com", "Colombia")
JULIANA = Customer("CLI-MD60UR8PNJDI", "80526117", "Juliana", "Castro Gómez", "juliana.castro@example.com", "México")
NO_EMAIL = Customer("CLI-MOCK00000000", "52917380", "Rosa Elena", "Díaz Mora", None, "Colombia")
GONZALEZ = [
    Customer(f"CLI-GONZ{index:08d}", f"4010{index:04d}", f"Cliente{index:02d}", "González Pérez", f"cliente{index}@example.com", "México")
    for index in range(22)
]
CUSTOMERS = [JUAN, ALICIA, JULIANA, NO_EMAIL, *GONZALEZ]

CESAR = Consultant("AGT-OJ9N4FGYV9", "E75612", "César", "González Sánchez", "cesar.gonzalez@example.com", "Active", "Créditos")
ON_VACATION = Consultant("AGT-TESTVAC001", "E20001", "Marta", "Ríos Vega", "marta.rios@example.com", "Vacation", "Cobranza")
ON_LEAVE = Consultant("AGT-TESTLEV001", "E20002", "Pablo", "Núñez Ortiz", "pablo.nunez@example.com", "Leave", None)
INACTIVE = Consultant("AGT-TESTINA001", "E20003", "Lucía", "Herrera Cruz", "lucia.herrera@example.com", "Inactive", "Ventas")
SHARED_CODE_DIEGO = Consultant("AGT-TESTSCA001", "E30001", "Diego", "Medina Paz", "diego.medina@example.com", "Active", "Fraudes")
SHARED_CODE_SOFIA = Consultant("AGT-TESTSCB001", "E30001", "Sofía", "Medina Lara", "sofia.medina@example.com", "Active", None)
SHARED_EMAIL_ANDRES = Consultant("AGT-TESTSEA001", "E40001", "Andrés", "Silva Mora", "equipo.silva@example.com", "Active", "Retención")
SHARED_EMAIL_VALERIA = Consultant("AGT-TESTSEB001", "E40002", "Valeria", "Silva Mora", "equipo.silva@example.com", "Active", "Ventas")
CONSULTANTS = [
    CESAR,
    ON_VACATION,
    ON_LEAVE,
    INACTIVE,
    SHARED_CODE_DIEGO,
    SHARED_CODE_SOFIA,
    SHARED_EMAIL_ANDRES,
    SHARED_EMAIL_VALERIA,
]


@dataclass(frozen=True)
class Login:
    role: Role
    code_path: str
    session_path: str
    identity: dict[str, str]


def customer_login(document_number: str) -> Login:
    return Login("customer", "/session/code", "/session", {"document_number": document_number})


def consultant_login(email: str, employee_code: str) -> Login:
    return Login("consultant", "/consultant/session/code", "/consultant/session", {"email": email, "employee_code": employee_code})


def login_of(consultant: Consultant) -> Login:
    return consultant_login(consultant.email, consultant.employee_code)


@dataclass
class FakeMailer:
    sent: list[tuple[str, str]] = field(default_factory=list)

    def send_login_code(self, to: str, code: str) -> None:
        self.sent.append((to, code))


@dataclass
class Harness:
    http: TestClient
    mail: FakeMailer

    def request_code(self, login: Login) -> dict[str, object]:
        response = self.http.post(login.code_path, json=login.identity)
        assert response.status_code == 200
        return response.json()

    def last_code(self) -> str:
        _, code = self.mail.sent[-1]
        return code

    def open_session(self, login: Login, code: str) -> int:
        return self.http.post(login.session_path, json={**login.identity, "code": code}).status_code

    def token(self, login: Login, code: str) -> str:
        response = self.http.post(login.session_path, json={**login.identity, "code": code})
        assert response.status_code == 200
        return response.json()["token"]


def seed_people(url: str) -> None:
    with psycopg.connect(url) as conn:
        conn.cursor().executemany(
            """
            INSERT INTO customers (customer_id, document_number, first_name, last_name, email, country, segment, customer_status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Basic', 'Active')
            """,
            [
                (c.customer_id, c.document_number, c.first_name, c.last_name, c.email, c.country)
                for c in CUSTOMERS
            ],
        )
        conn.cursor().executemany(
            """
            INSERT INTO service_agents (agent_id, employee_code, first_name, last_name, email, agent_status, specialty)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (c.consultant_id, c.employee_code, c.first_name, c.last_name, c.email, c.status, c.specialty)
                for c in CONSULTANTS
            ],
        )
