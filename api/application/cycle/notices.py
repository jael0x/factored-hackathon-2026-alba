from api.application.cycle.context import Cycle, Trigger, WrongTrigger, expect, process_id_of, process_of, stored
from api.contract_models import Locale, ProductKey, RuleId, TemplateId
from api.domain.policy.templates import handoff_notice, render_notice
from api.domain.process.commands import PRODUCT_CASE_OPEN, CommandPayload, NoPayload, TemplatePayload
from api.domain.process.lifecycle import POLICY_REFER
from api.domain.process.new_events import Appended, template_sent
from api.domain.process.stored_events import (
    AnalysisCompleted,
    AppealRequested,
    ConsultantClosed,
    MessageReceived,
    PrequalificationDecided,
    ProcessStarted,
    ShownTurn,
    StoredEvent,
    ThreadTaken,
    WithheldTurn,
)
from api.domain.process.thread import ASSISTANT_AUTHOR, TEMPLATE_AUTHOR


def send_template(cycle: Cycle, trigger: Trigger, payload: CommandPayload) -> None:
    template_id = expect(payload, TemplatePayload).template_id
    process = process_of(cycle, trigger)
    event = trigger.event
    locale, body = (
        handoff_text(cycle, trigger, event) if isinstance(event, ThreadTaken) else notice_text(event, template_id)
    )
    result = cycle.events.append(template_sent(process, locale, template_id, body, trigger.cause))
    if isinstance(result, Appended):
        cycle.thread.add_line(process.process_id, TEMPLATE_AUTHOR, body, result.event_id)


def notice_text(event: StoredEvent, template_id: TemplateId) -> tuple[Locale, str]:
    locale, product = notice_context(event, template_id)
    return locale, render_notice(template_id, locale, product)


def notice_context(event: StoredEvent, template_id: TemplateId) -> tuple[Locale, ProductKey | None]:
    if isinstance(event, ShownTurn) and template_id == PRODUCT_CASE_OPEN:
        return event.locale, event.open_case_product
    if isinstance(event, ShownTurn | AnalysisCompleted):
        return event.locale, event.product
    raise WrongTrigger("a shown turn, an analysis, or a handoff", event)


# conversation.thread_taken carries neither locale nor rule, so both come from the event that caused the handoff:
# the analysis, the turn, the appeal, or the failed command's trigger (PLAN.md D28).
def handoff_text(cycle: Cycle, trigger: Trigger, taken: ThreadTaken) -> tuple[Locale, str]:
    cause = handoff_cause(cycle, trigger)
    locale = locale_carried_by(cause)
    rule = deciding_rule_of(cause) if taken.reason_code == POLICY_REFER else None
    return locale, handoff_notice(locale, cycle.case.product_of(process_id_of(trigger)), taken.reason_code, rule)


def handoff_cause(cycle: Cycle, trigger: Trigger) -> StoredEvent:
    cause_id = trigger.row.caused_by_event_id
    if cause_id is None:
        raise LookupError(f"handoff {trigger.row.event_id} names no cause")
    return stored(cycle.log.read(cause_id))


def locale_carried_by(event: StoredEvent) -> Locale:
    if isinstance(
        event,
        MessageReceived
        | ShownTurn
        | WithheldTurn
        | AnalysisCompleted
        | ProcessStarted
        | PrequalificationDecided
        | ConsultantClosed
        | AppealRequested,
    ):
        return event.locale
    raise WrongTrigger("an event that carries a locale", event)


def deciding_rule_of(cause: StoredEvent) -> RuleId:
    return expect(cause, AnalysisCompleted).deciding_rule


def show_reply(cycle: Cycle, trigger: Trigger, payload: CommandPayload) -> None:
    expect(payload, NoPayload)
    turn = expect(trigger.event, ShownTurn)
    cycle.thread.add_line(process_id_of(trigger), ASSISTANT_AUTHOR, turn.reply_text, turn.event_id)
