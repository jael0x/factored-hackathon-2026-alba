from api.application.cycle.context import Cycle, Trigger, WrongTrigger, expect, process_id_of, process_of
from api.contract_models import Locale, ProductKey
from api.domain.policy.templates import render_notice
from api.domain.process.commands import CommandPayload, NoPayload, TemplatePayload
from api.domain.process.new_events import Appended, template_sent
from api.domain.process.stored_events import AnalysisCompleted, ShownTurn, StoredEvent
from api.domain.process.thread import ASSISTANT_AUTHOR, TEMPLATE_AUTHOR


def send_template(cycle: Cycle, trigger: Trigger, payload: CommandPayload) -> None:
    template_id = expect(payload, TemplatePayload).template_id
    locale, product = notice_context(trigger.event)
    process = process_of(cycle, trigger)
    body = render_notice(template_id, locale, product)
    result = cycle.events.append(template_sent(process, locale, template_id, body, trigger.cause))
    if isinstance(result, Appended):
        cycle.thread.add_line(process.process_id, TEMPLATE_AUTHOR, body, result.event_id)


def notice_context(event: StoredEvent) -> tuple[Locale, ProductKey | None]:
    if isinstance(event, ShownTurn | AnalysisCompleted):
        return event.locale, event.product
    raise WrongTrigger("a shown turn or an analysis", event)


def show_reply(cycle: Cycle, trigger: Trigger, payload: CommandPayload) -> None:
    expect(payload, NoPayload)
    turn = expect(trigger.event, ShownTurn)
    cycle.thread.add_line(process_id_of(trigger), ASSISTANT_AUTHOR, turn.reply_text, turn.event_id)
