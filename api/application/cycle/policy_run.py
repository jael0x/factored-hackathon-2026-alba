from api.application.cycle.context import Cycle, Trigger, WrongTrigger, expect, require_case, require_profile
from api.contract_models import Locale
from api.domain.policy.declared_income import income_for_run
from api.domain.policy.engine import decide
from api.domain.process.commands import CommandPayload, PolicyRunPayload
from api.domain.process.new_events import analysis_completed
from api.domain.process.stored_events import MessageReceived, ShownTurn, StoredEvent


def run_policy(cycle: Cycle, trigger: Trigger, payload: CommandPayload) -> None:
    run = expect(payload, PolicyRunPayload)
    locale = run_locale(trigger.event)
    process = require_case(cycle, trigger)
    profile = require_profile(cycle, trigger.row.customer_id)
    income = income_for_run(profile, run.declared_income_amount, run.declared_income_currency)
    decision = decide(profile, run.product, income)
    cycle.events.append(analysis_completed(process, decision, run.product, locale, trigger.cause))


# A consented turn, or the start the home's dialog sends with the consent already given (D24).
def run_locale(event: StoredEvent) -> Locale:
    if isinstance(event, ShownTurn | MessageReceived):
        return event.locale
    raise WrongTrigger("a shown turn or a start", event)
