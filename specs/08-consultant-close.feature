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

  Scenario: The customer's certificate from a consultant shows no income figures
    Given César closed Alicia's credit card case as pre-qualified
    When Alicia opens her certificate
    Then it says a person from the bank reviewed her request and she pre-qualifies for a credit card
    And it shows no income and no USD equivalent
    And it offers no option to ask a person to review it
