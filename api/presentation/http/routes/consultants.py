from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.contract_models import ConsultantSearchHit, ConsultantSearchResults, CurrentConsultant
from api.domain.consultants.identity import ConsultantHit
from api.domain.search import RejectedSearch
from api.domain.session.tokens import SessionClaims
from api.presentation.http.dependencies import (
    ReadCurrentConsultant,
    RunConsultantSearch,
    get_demo_login,
    get_read_current_consultant,
    get_run_consultant_search,
    require_consultant,
)
from api.presentation.http.errors import invalid_body, not_found, unauthorized

router = APIRouter()
search = APIRouter(prefix="/consultants")


@router.get("/consultant/me", response_model=CurrentConsultant)
def read_me(
    session: Annotated[SessionClaims, Depends(require_consultant)],
    read_consultant: Annotated[ReadCurrentConsultant, Depends(get_read_current_consultant)],
) -> CurrentConsultant:
    consultant = read_consultant(session.sub)
    if consultant is None:
        raise unauthorized()
    return CurrentConsultant(
        consultant_id=consultant.consultant_id,
        employee_code=consultant.employee_code,
        first_name=consultant.first_name,
        last_name=consultant.last_name,
        specialty=consultant.specialty,
    )


@search.get("/search", response_model=ConsultantSearchResults)
def search_consultants(
    run: Annotated[RunConsultantSearch, Depends(get_run_consultant_search)],
    demo_login: Annotated[bool, Depends(get_demo_login)],
    q: Annotated[str | None, Query(min_length=1)] = None,
    random: bool | None = None,
) -> ConsultantSearchResults:
    if not demo_login:
        raise not_found()
    found = run(q, random)
    if isinstance(found, RejectedSearch):
        raise invalid_body()
    return ConsultantSearchResults(consultants=[_wire_hit(hit) for hit in found])


def _wire_hit(hit: ConsultantHit) -> ConsultantSearchHit:
    return ConsultantSearchHit(
        consultant_id=hit.consultant_id,
        employee_code=hit.employee_code,
        first_name=hit.first_name,
        last_name=hit.last_name,
        email=hit.email,
    )


router.include_router(search)
