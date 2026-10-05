from api.application.cycle.context import Cycle, Trigger, expect, process_of, require_profile
from api.domain.policy.declared_income import income_for_run
from api.domain.policy.engine import decide
from api.domain.process.commands import CommandPayload, PolicyRunPayload
from api.domain.process.new_events import analysis_completed
from api.domain.process.stored_events import ShownTurn


def run_policy(cycle: Cycle, trigger: Trigger, payload: CommandPayload) -> None:
    run = expect(payload, PolicyRunPayload)
    turn = expect(trigger.event, ShownTurn)
    process = process_of(cycle, trigger)
    profile = require_profile(cycle, trigger.row.customer_id)
    income = income_for_run(profile, run.declared_income_amount, run.declared_income_currency)
    decision = decide(profile, run.product, income)
    cycle.events.append(analysis_completed(process, decision, run.product, turn.locale, trigger.cause))
