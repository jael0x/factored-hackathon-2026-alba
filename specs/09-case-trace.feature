Feature: Case trace
  As a credit agent
  I want to read every recorded step of a case in order
  So that I can see why the system did what it did

  Background:
    Given Alicia Mariana Parra Álvarez wrote "quiero una tarjeta de crédito" in a new case
    And she confirmed the pre-qualification with "sí"
    And her request was referred by rule "R05"

  Scenario: The trace lists the case events in the order they happened
    When César González Sánchez opens the trace of Alicia's case
    Then he sees these events in this order:
      | event                         | detail                        |
      | conversation.message_received | quiero una tarjeta de crédito |
      | process.started               | credit_prequalification       |
      | conversation.turn_classified  | prequalify_card               |
      | conversation.template_sent    | confirm_prequalify            |
      | conversation.message_received | sí                            |
      | conversation.turn_classified  | confirm_prequalify            |
      | analysis.completed            | REFER by R05                  |
      | conversation.template_sent    | refer_notice                  |
      | process.state_changed         | ai_active to human_active     |
      | conversation.thread_taken     | policy_refer                  |

  Scenario: The trace shows the facts behind the decision
    When César opens the trace of Alicia's case
    Then the policy analysis cites this fact:
      | name         | value | source                               | as-of      |
      | credit_score | 615   | customer_credit_profile.credit_score | 2026-06-17 |
    And it names rule "R05" under policy "alba-credit-v1"

  Scenario: The trace shows how each message was classified
    When César opens the trace of Alicia's case
    Then the first classified turn shows the intent "prequalify_card" and the product "credit_card"
    And the second classified turn shows the intent "confirm_prequalify"
