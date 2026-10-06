Feature: Case trace
  As a credit consultant
  I want to read every recorded step of a case in order
  So that I can see why the system did what it did

  Background:
    Given Alicia Mariana Parra Álvarez started a credit card request from her home
    And her request was referred by rule "R05"

  Scenario: The trace lists the case events in the order they happened
    When César González Sánchez opens the trace of Alicia's case
    Then he sees these events in this order:
      | event                         | detail                        |
      | conversation.message_received | Quiero una tarjeta de crédito |
      | process.started               | credit_prequalification       |
      | analysis.completed            | REFER by R05                  |
      | process.state_changed         | ai_active to human_active     |
      | conversation.thread_taken     | policy_refer                  |
      | conversation.template_sent    | refer_notice                  |

  Scenario: The trace shows the facts behind the decision
    When César opens the trace of Alicia's case
    Then the policy analysis cites these facts:
      | name            | value         | source                                  | as-of      |
      | credit_score    | 615           | customer_credit_profile.credit_score    | 2026-06-17 |
      | income_local    | 4707334.28    | customer_credit_profile.income_local    | 2026-06-17 |
      | income_currency | COP           | customer_credit_profile.income_currency | 2026-06-17 |
      | income_usd      | 1167.41890144 | customer_credit_profile.income_usd      | 2026-06-17 |
    And it names rule "R05" under policy "alba-credit-v1"
    And it lists the rules it evaluated, in this order:
      | rule | result |
      | R01  | passed |
      | R02  | passed |
      | R03  | passed |
      | R09  | passed |
      | R04  | passed |
      | R06  | passed |
      | R05  | REFER  |

  Scenario: A message written while the case waits for a person is recorded and not classified
    Given Alicia wrote "¿ya revisaron mi caso?" after her case went to a person
    When César opens the trace of Alicia's case
    Then the last event is her message "¿ya revisaron mi caso?"
    And no classified turn follows it

  Scenario: Every kind of event shows the fields it was recorded with
    When César opens the trace of any case
    Then each event shows this detail:
      | event                           | detail                                                                                                  |
      | conversation.message_received   | the text                                                                                                |
      | process.started                 | process_key                                                                                             |
      | conversation.turn_classified    | intent, product, and language; the declared amount and its currency when one was read; reason_code when the reply was withheld |
      | conversation.template_sent      | template_id                                                                                             |
      | conversation.consultant_closed  | outcome by consultant_id                                                                                |
      | conversation.thread_taken       | reason_code                                                                                             |
      | analysis.completed              | outcome by deciding_rule                                                                                |
      | prequalification.decided        | outcome and decided_by                                                                                  |
      | process.state_changed           | from_state to to_state, and end_reason when there is one                                               |
      | process.ended                   | end_reason, and policy_version when there is one                                                        |
      | conversation.appeal_requested   | product                                                                                                 |
    And every value is shown as it was recorded, with no rounding and no thousands separator

  Scenario: Each event names the event that caused it
    When César opens the trace of Alicia's case
    Then "process.started" says it was caused by event 1, her message
    And her message names no cause
