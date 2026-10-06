from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import psycopg
from pydantic import BaseModel, ConfigDict, Strict

from api.contract_models import EndReason, IncomeCurrency, Outcome, ProcessState, RuleId
from api.domain.policy.engine import CreditProfile, CustomerStatus
from api.infrastructure.llm.schema import decode_exact_json

ORACLE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "oracle_customers.json"

# decode_exact_json reads every number as a Decimal, a date as text, and an array as a list, so these convert.
WholeNumber = Annotated[int, Strict(False)]
IsoDate = Annotated[date, Strict(False)]


class OracleModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class OracleProduct(OracleModel):
    product_id: str
    product_type: str
    currency: str
    current_balance: Decimal
    product_status: str
    days_past_due: WholeNumber | None


class OracleResult(OracleModel):
    outcome: Outcome
    deciding_rule: RuleId
    state: ProcessState
    end_reason: EndReason | None


class OracleDeclaredIncome(OracleModel):
    declared_income: Decimal
    outcome: Outcome
    deciding_rule: RuleId


class OracleCustomer(OracleModel):
    customer_id: str
    first_name: str
    last_name: str
    country: str
    segment: str
    customer_status: CustomerStatus
    credit_score: WholeNumber | None
    income_local: Decimal | None
    income_currency: IncomeCurrency | None
    income_usd: Decimal | None
    max_days_past_due: WholeNumber
    has_active_card: bool
    has_active_personal_loan: bool
    has_email: bool
    products: Annotated[tuple[OracleProduct, ...], Strict(False)]
    expected: OracleResult
    after_declared_income: OracleDeclaredIncome | None


class OracleConsultant(OracleModel):
    consultant_id: str
    employee_code: str
    first_name: str
    last_name: str
    status: str
    specialty: str
    has_email: bool


class Oracle(OracleModel):
    as_of: IsoDate
    rates_to_usd: dict[IncomeCurrency, Decimal]
    product_types: Annotated[tuple[str, ...], Strict(False)]
    customers: Annotated[tuple[OracleCustomer, ...], Strict(False)]
    consultant: OracleConsultant


def load_oracle(path: Path = ORACLE_PATH) -> Oracle:
    return Oracle.model_validate(decode_exact_json(path.read_bytes()))


ORACLE = load_oracle()


def oracle_customer(customer_id: str) -> OracleCustomer:
    [customer] = [c for c in ORACLE.customers if c.customer_id == customer_id]
    return customer


def credit_profile_of(customer: OracleCustomer) -> CreditProfile:
    return CreditProfile(
        customer_status=customer.customer_status,
        credit_score=customer.credit_score,
        income_local=customer.income_local,
        income_currency=customer.income_currency,
        income_usd=customer.income_usd,
        max_days_past_due=customer.max_days_past_due,
        has_active_card=customer.has_active_card,
        has_active_personal_loan=customer.has_active_personal_loan,
        as_of=ORACLE.as_of,
    )


def seed_oracle_profiles(conn: psycopg.Connection) -> None:
    conn.cursor().executemany(
        """
        INSERT INTO customer_credit_profile (
            customer_id, first_name, last_name, country, segment, customer_status, credit_score, income_local,
            income_currency, income_usd, max_days_past_due, has_active_card, has_active_personal_loan, as_of, batch_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            (
                c.customer_id,
                c.first_name,
                c.last_name,
                c.country,
                c.segment,
                c.customer_status,
                c.credit_score,
                c.income_local,
                c.income_currency,
                c.income_usd,
                c.max_days_past_due,
                c.has_active_card,
                c.has_active_personal_loan,
                ORACLE.as_of,
                uuid4(),
            )
            for c in ORACLE.customers
        ],
    )
