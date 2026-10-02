from api.application.session.ports import Consultants
from api.domain.consultants.identity import ConsultantIdentity


def read_current_consultant(consultants: Consultants, consultant_id: str) -> ConsultantIdentity | None:
    return consultants.find_by_id(consultant_id)
