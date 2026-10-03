from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CustomerProduct:
    product_id: str
    product_type: str
    product_number: str
    currency: str
    current_balance: Decimal
    product_status: str
