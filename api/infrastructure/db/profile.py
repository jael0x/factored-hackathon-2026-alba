import psycopg

from api.domain.closed_sets import parse_member
from api.domain.policy.engine import CreditProfile, parse_customer_status
from api.domain.process.stored_events import INCOME_CURRENCIES


class PostgresProfiles:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def read(self, customer_id: str) -> CreditProfile | None:
        row = self._conn.execute(
            """
            SELECT customer_status, credit_score, income_local, income_currency, income_usd,
                   max_days_past_due, has_active_card, has_active_personal_loan, as_of
            FROM customer_credit_profile
            WHERE customer_id = %s
            """,
            (customer_id,),
        ).fetchone()
        if row is None:
            return None
        status, score, income_local, currency, income_usd, days, card, loan, as_of = row
        return CreditProfile(
            customer_status=parse_customer_status(status),
            credit_score=score,
            income_local=income_local,
            income_currency=None if currency is None else parse_member(currency, INCOME_CURRENCIES, "income_currency"),
            income_usd=income_usd,
            max_days_past_due=days,
            has_active_card=card,
            has_active_personal_loan=loan,
            as_of=as_of,
        )
