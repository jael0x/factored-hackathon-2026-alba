import logging

from api.application.cycle.context import Cycle, Trigger, expect, read_process, require_profile, stored
from api.application.cycle.ports import TurnRequest
from api.domain.policy.engine import CreditProfile
from api.domain.process.commands import CommandPayload, NoPayload
from api.domain.process.lifecycle import AI_ACTIVE, CREDIT_PREQUALIFICATION, ProcessRow
from api.domain.process.new_events import turn_classified
from api.domain.process.stored_events import MessageReceived
from api.domain.process.turns import stamp_turn

logger = logging.getLogger(__name__)


def classify_message(cycle: Cycle, trigger: Trigger, payload: CommandPayload) -> None:
    expect(payload, NoPayload)
    message = expect(trigger.event, MessageReceived)
    process = case_of_message(cycle, trigger, message)
    if process.state != AI_ACTIVE:
        logger.info("message %s reached a %s case; the model is not called", message.event_id, process.state)
        return
    profile = require_profile(cycle, trigger.row.customer_id)
    earlier = [stored(row) for row in cycle.log.earlier(process.process_id, trigger.row.seq)]
    model = cycle.read_turn(turn_request(message, process, profile))
    stamp = stamp_turn(earlier, model.reading.product, cycle.case.product_of(process.process_id))
    cycle.case.store_turn_facts(process.process_id, message.locale, stamp.product)
    cycle.events.append(turn_classified(process, message.locale, model, stamp, trigger.cause))


def case_of_message(cycle: Cycle, trigger: Trigger, message: MessageReceived) -> ProcessRow:
    if message.process_id is not None:
        return read_process(cycle, message.process_id)
    opened = cycle.processes.find_open(trigger.row.customer_id, CREDIT_PREQUALIFICATION)
    if opened is None:
        raise LookupError(f"message {message.event_id} has no process and its customer has no open case")
    return opened


def turn_request(message: MessageReceived, process: ProcessRow, profile: CreditProfile) -> TurnRequest:
    return TurnRequest(
        text=message.text,
        locale=message.locale,
        process_state=process.state,
        income_on_file=profile.income_local is not None,
        score_on_file=profile.credit_score is not None,
        has_active_card=profile.has_active_card,
        has_active_personal_loan=profile.has_active_personal_loan,
    )
