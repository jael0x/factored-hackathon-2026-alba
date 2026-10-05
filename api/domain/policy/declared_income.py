from decimal import Decimal

from api.contract_models import IncomeCurrency
from api.domain.policy.engine import CreditProfile


def income_for_run(profile: CreditProfile, amount: Decimal | None, currency: IncomeCurrency | None) -> Decimal | None:
    if currency is not None and currency != profile.income_currency:
        return None
    return amount
