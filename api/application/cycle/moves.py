from api.application.cycle.context import Cycle, Trigger, expect, process_id_of, stored
from api.application.processes import end_process, hand_off_process, start_process
from api.contract_models import PolicyVersion
from api.domain.process.commands import DECIDED_BY_POLICY, CommandPayload, EndPayload, StartPayload, TransitionPayload
from api.domain.process.lifecycle import HUMAN_ACTIVE
from api.domain.process.stored_events import AnalysisCompleted, PrequalificationDecided


def open_case(cycle: Cycle, trigger: Trigger, payload: CommandPayload) -> None:
    start = expect(payload, StartPayload)
    start_process(cycle.events, cycle.processes, trigger.row.customer_id, start.locale, trigger.cause)


def hand_off_case(cycle: Cycle, trigger: Trigger, payload: CommandPayload) -> None:
    move = expect(payload, TransitionPayload)
    if move.to_state != HUMAN_ACTIVE:
        raise ValueError(f"process.transition only moves a case to {HUMAN_ACTIVE}, not {move.to_state}")
    hand_off_process(cycle.events, cycle.processes, process_id_of(trigger), move.reason_code, trigger.cause)


def end_case(cycle: Cycle, trigger: Trigger, payload: CommandPayload) -> None:
    end = expect(payload, EndPayload)
    version = policy_version_behind(cycle, trigger)
    end_process(cycle.events, cycle.processes, process_id_of(trigger), end.end_reason, version, trigger.cause)


def policy_version_behind(cycle: Cycle, trigger: Trigger) -> PolicyVersion | None:
    decided = trigger.event
    if not isinstance(decided, PrequalificationDecided) or decided.decided_by != DECIDED_BY_POLICY:
        return None
    analysis_id = trigger.row.caused_by_event_id
    if analysis_id is None:
        raise LookupError(f"policy certificate {decided.event_id} names no analysis")
    return expect(stored(cycle.log.read(analysis_id)), AnalysisCompleted).policy_version
