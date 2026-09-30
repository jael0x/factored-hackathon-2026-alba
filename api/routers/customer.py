from typing import Annotated

from fastapi import APIRouter, Depends

from api import customers, db
from api.auth import SessionClaims, require_customer
from api.contract_models import CurrentCustomer
from api.errors import unauthorized

router = APIRouter()


@router.get("/me", response_model=CurrentCustomer)
def read_current_customer(session: Annotated[SessionClaims, Depends(require_customer)]) -> CurrentCustomer:
    with db.connect() as conn:
        customer = customers.find_by_id(conn, session.sub)
    if customer is None:
        raise unauthorized()
    return CurrentCustomer(customer_id=customer.customer_id, first_name=customer.first_name, last_name=customer.last_name)
