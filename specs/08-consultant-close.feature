Feature: Consultant close
  As a credit consultant
  I want to close a referred case as pre-qualified or not
  So that the customer gets a clear answer written by the bank, not by me or the model

  Background:
    Given Alicia Mariana Parra Álvarez's credit card request was referred by rule "R05"
    And César González Sánchez is signed in as a consultant

  Scenario: The review queue lists only cases waiting for a person
    Given Juan's case ended as pre-qualified
    And Mariana's case ended as not pre-qualified
    When César opens the review queue
    Then he sees Alicia's case
    And he does not see Juan's case
    And he does not see Mariana's case

  Scenario: The case shows the handoff packet
    When César opens Alicia's case
    Then he sees this packet:
      | field   | value            |
      | request | credit card      |
      | score   | 615              |
      | income  | 4,707,334.28 COP |
      | rule    | R05              |
      | policy  | alba-credit-v1   |

  Scenario: The case shows the customer's conversation, read only
    Given Alicia wrote "já revisaram meu caso?" while her case waited for a person
    When César opens Alicia's case
    Then he sees her conversation as she sees it, ending with "já revisaram meu caso?"

  Scenario: The consultant has no way to write in the thread
    When César opens Alicia's case
    Then the only actions are to close as pre-qualified or as not pre-qualified
    And there is no field to reply to Alicia

  Scenario: The outcome is written in the customer's language, not the consultant's
    Given Alicia chose Portuguese in the language switch before her case was referred
    And César reads the review queue in Spanish
    When César closes Alicia's case as "PREQUALIFIED"
    Then Alicia's automatic message is written in Portuguese

  Scenario Outline: Closing the case sends the customer the outcome
    When César closes Alicia's case as "<outcome>"
    Then Alicia receives the automatic message for "<outcome>"
    And her case ends as "<end-reason>"
    And her case leaves the review queue

    Examples:
      | outcome          | end-reason       |
      | PREQUALIFIED     | prequalified     |
      | NOT_PREQUALIFIED | not_prequalified |

  Scenario: Closing does not run the policy again
    When César closes Alicia's case as "PREQUALIFIED"
    Then Alicia's case trace shows one policy analysis

  Scenario: A closed case cannot be closed again
    Given César closed Alicia's case as "NOT_PREQUALIFIED"
    When a second close arrives for Alicia's case as "PREQUALIFIED"
    Then her case stays closed as not pre-qualified
    And Alicia receives no second message

  Scenario: The consultant cannot close with any other outcome
    When César tries to close Alicia's case as "REFER"
    Then the close is rejected
    And Alicia's case stays in the review queue

  Scenario: A case the policy left without a result cannot be closed
    Given Juliana Castro Gómez was asked for her monthly income in her credit card case
    And she wrote "quiero hablar con una persona" in that case
    When César opens Juliana's case
    Then he sees the reason "customer_requested_human" and the outcome "NEEDS_INFO" by rule "R06"
    And the case offers no way to close it
    When César tries to close Juliana's case as "PREQUALIFIED"
    Then the close is refused
    And Juliana's case stays in the review queue

  Scenario: A case handed off before the policy ran shows no analysis and cannot be closed
    Given a customer with no credit profile started a credit card request
    And the policy could not run, so the case went to a person with reason "tool_failed"
    When César opens that case
    Then the packet shows no score, no income, no rule, no policy, and no outcome
    And the case offers no way to close it

  Scenario: The customer's certificate from a consultant shows no income figures
    Given César closed Alicia's credit card case as pre-qualified
    When Alicia opens her certificate
    Then it says a person from the bank reviewed her request and she pre-qualifies for a credit card
    And it shows no income and no USD equivalent
    And it offers no option to ask a person to review it

  Scenario: A case page left open shows the close once it is reloaded
    Given Alicia's case page says a person is seeing her case
    And César closed her case as pre-qualified
    When Alicia reloads that page
    Then she sees her certificate
    And the page no longer says a person is seeing her case
