Feature: Pre-qualification decision
  As a bank customer
  I want a decision from the bank's written policy
  So that the answer is the same every time and does not depend on how I phrase it

  Scenario: Juan pre-qualifies for a credit card
    Given Juan Alberto Romero González has a credit score of 812 and income on file
    And he has no credit product past due
    And he holds no active credit card
    And the assistant asked Juan whether to start the pre-qualification for a credit card
    When Juan writes "sí"
    Then Juan sees a certificate that says he pre-qualifies for a credit card
    And his case ends as pre-qualified

  Scenario: The certificate shows income in local currency with its USD equivalent
    Given Juan pre-qualified for a credit card
    When Juan opens his certificate
    Then it shows his income as 306,753.45 MXN
    And it shows the equivalent of 17,988 USD at the exchange rate of June 17, 2026

  Scenario: The certificate carries no credit limit and no rate
    Given Juan pre-qualified for a credit card
    When Juan opens his certificate
    Then it shows no credit limit
    And it shows no interest rate for the new product

  Scenario: Delinquency decides before the credit score
    Given Mariana Mónica Acosta Rojas has a credit card 180 days past due
    And her credit score is 515
    When Mariana confirms the pre-qualification for a personal loan
    Then Mariana sees a certificate that says she does not pre-qualify
    And the decision names rule "R02" as the deciding rule

  Scenario Outline: Customer status decides before anything else
    Given a customer with status "<status>" and a credit score of 750
    When the customer confirms the pre-qualification for a credit card
    Then the outcome is "<outcome>"

    Examples:
      | status    | outcome          |
      | Suspended | REFER            |
      | Inactive  | REFER            |
      | Closed    | NOT_PREQUALIFIED |

  Scenario Outline: Days past due on a credit product set the outcome
    Given an active customer with a credit score of 750 and income on file
    And the customer's most delinquent credit product is <days> days past due
    When the customer confirms the pre-qualification for a personal loan
    Then the outcome is "<outcome>"

    Examples:
      | days | outcome          |
      | 1    | REFER            |
      | 29   | REFER            |
      | 30   | NOT_PREQUALIFIED |

  Scenario: A customer who already holds the product is referred
    Given an active customer with a credit score of 750 and no credit product past due
    And the customer holds an active credit card
    When the customer confirms the pre-qualification for a credit card
    Then the outcome is "REFER"

  Scenario: A customer with no credit score is referred without being asked for it
    Given an active customer with no credit score on file and no credit product past due
    When the customer confirms the pre-qualification for a personal loan
    Then the outcome is "REFER"
    And the assistant does not ask for a credit score

  Scenario Outline: The credit score band sets the outcome
    Given an active customer with income on file and no credit product past due
    And the customer holds no active credit card
    And the customer's credit score is <score>
    When the customer confirms the pre-qualification for a credit card
    Then the outcome is "<outcome>"

    Examples:
      | score | outcome          |
      | 579   | NOT_PREQUALIFIED |
      | 580   | REFER            |
      | 619   | REFER            |
      | 620   | PREQUALIFIED     |

  Scenario Outline: The certificate is written in the language the customer chose
    Given Juan Alberto Romero González chose <language> in the language switch
    And the assistant asked him in <language> whether to start the pre-qualification for a credit card
    When Juan writes "<yes>"
    Then Juan sees his certificate in <language>

    Examples:
      | language   | yes |
      | Spanish    | sí  |
      | Portuguese | sim |

  Scenario: A message delivered twice does not produce a second decision
    Given Juan's confirmation "sí" produced a certificate
    When the app delivers the same message a second time
    Then Juan still has one certificate

  Scenario: A new message after an ended case opens a new case
    Given Juan's credit card case ended as pre-qualified
    When Juan writes "quiero un préstamo personal"
    Then a new case opens for Juan
    And the ended case stays closed

  Scenario: A message id sent again with another text is refused
    Given Juan sent "sí" with a message id
    When the app sends "no" with the same message id
    Then the app is told that message id was already used
    And Juan's conversation still shows "sí" once and no "no"

  Scenario: Two messages sent before the case opens join one case
    Given Juan has no open case
    When Juan writes "quiero una tarjeta de crédito" and then "y también un préstamo" before the first is answered
    Then Juan has one open case
    And both messages are in that case's conversation
