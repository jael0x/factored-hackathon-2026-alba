from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.contract_models import CurrentCustomer, CustomerSearchHit, CustomerSearchResults
from api.domain.customers.identity import CustomerHit
from api.domain.search import RejectedSearch
from api.domain.session.tokens import SessionClaims
from api.presentation.http.dependencies import (
    ReadCurrentCustomer,
    RunCustomerSearch,
    get_demo_login,
    get_read_current_customer,
    get_run_customer_search,
    require_customer,
)
from api.presentation.http.errors import invalid_body, not_found, unauthorized

router = APIRouter()
search = APIRouter(prefix="/customers")


@router.get("/me", response_model=CurrentCustomer)
def read_me(
    session: Annotated[SessionClaims, Depends(require_customer)],
    read_customer: Annotated[ReadCurrentCustomer, Depends(get_read_current_customer)],
) -> CurrentCustomer:
    customer = read_customer(session.sub)
    if customer is None:
        raise unauthorized()
    return CurrentCustomer(customer_id=customer.customer_id, first_name=customer.first_name, last_name=customer.last_name)


@search.get("/search", response_model=CustomerSearchResults)
def search_customers(
    run: Annotated[RunCustomerSearch, Depends(get_run_customer_search)],
    demo_login: Annotated[bool, Depends(get_demo_login)],
    q: Annotated[str | None, Query(min_length=1)] = None,
    random: bool | None = None,
) -> CustomerSearchResults:
    if not demo_login:
        raise not_found()
    found = run(q, random)
    if isinstance(found, RejectedSearch):
        raise invalid_body()
    return CustomerSearchResults(customers=[_wire_hit(hit) for hit in found])


def _wire_hit(hit: CustomerHit) -> CustomerSearchHit:
    return CustomerSearchHit(
        customer_id=hit.customer_id,
        document_number=hit.document_number,
        first_name=hit.first_name,
        last_name=hit.last_name,
        country=hit.country,
    )


router.include_router(search)
