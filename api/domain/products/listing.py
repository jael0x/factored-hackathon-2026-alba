from api.domain.products.product import CustomerProduct

CLOSED_STATUS = "Closed"

LOAN_TYPES = frozenset({"Préstamo Personal", "Préstamo Hipotecario"})


def is_paid_loan(product: CustomerProduct) -> bool:
    return product.product_type in LOAN_TYPES and product.current_balance == 0


def is_listed(product: CustomerProduct) -> bool:
    return product.product_status != CLOSED_STATUS and not is_paid_loan(product)
