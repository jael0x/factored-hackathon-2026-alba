from api.application.cycle.context import Cycle, Trigger, expect, process_of
from api.contract_models import CloseOutcome, DecidedBy, Locale
from api.domain.closed_sets import parse_member
from api.domain.policy.templates import certificate_for_close, certificate_for_policy
from api.domain.process.commands import DECIDED_BY_POLICY, CommandPayload, RenderPayload
from api.domain.process.lifecycle import ProcessRow
from api.domain.process.new_events import Appended, prequalification_decided
from api.domain.process.stored_events import CLOSE_OUTCOMES, AnalysisCompleted, ConsultantClosed, StoredEvent
from api.domain.process.thread import TEMPLATE_AUTHOR


def render_decision(cycle: Cycle, trigger: Trigger, payload: CommandPayload) -> None:
    decided_by = expect(payload, RenderPayload).decided_by
    process = process_of(cycle, trigger)
    outcome, locale, body = certificate(cycle, trigger.event, process, decided_by)
    result = cycle.events.append(prequalification_decided(process, locale, outcome, body, decided_by, trigger.cause))
    if isinstance(result, Appended):
        cycle.thread.add_line(process.process_id, TEMPLATE_AUTHOR, body, result.event_id)


def certificate(
    cycle: Cycle, event: StoredEvent, process: ProcessRow, decided_by: DecidedBy
) -> tuple[CloseOutcome, Locale, str]:
    if (decided_by == DECIDED_BY_POLICY) != isinstance(event, AnalysisCompleted):
        raise ValueError(f"a {decided_by} certificate cannot follow {type(event).__name__}")
    if isinstance(event, AnalysisCompleted):
        outcome = parse_member(event.outcome, CLOSE_OUTCOMES, "certificate outcome")
        return outcome, event.locale, certificate_for_policy(outcome, event.locale, event.product)
    closed = expect(event, ConsultantClosed)
    product = cycle.case.product_of(process.process_id)
    return closed.outcome, closed.locale, certificate_for_close(closed.outcome, closed.locale, product)
