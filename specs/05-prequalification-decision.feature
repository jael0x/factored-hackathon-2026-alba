Feature: Pre-qualification decision
  As a bank customer
  I want a decision from the bank's written policy
  So that the answer is the same every time and does not depend on how I phrase it

  Scenario: Juan pre-qualifies for a credit card
    Given Juan Alberto Romero González has a credit score of 812 and income on file
    And he has no credit product past due
    And he holds no active credit card
    When Juan starts a credit card request from his home
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
    When Juan starts a credit card request from his home
    Then Juan sees his certificate in <language>

    Examples:
      | language   |
      | Spanish    |
      | Portuguese |

  Scenario: A start delivered twice does not produce a second decision
    Given Juan's credit card start produced a certificate
    When the app delivers the same start a second time
    Then Juan still has one certificate

  Scenario: An ended case takes no new message
    Given Juan's credit card case ended as pre-qualified
    When Juan opens that case
    Then he sees the certificate and "Volver al inicio" instead of a message box
    And a message the app sends to that case is refused as ended

  Scenario: A message id sent again with another text is refused
    Given Juan sent "sí" with a message id
    When the app sends "no" with the same message id
    Then the app is told that message id was already used
    And Juan's conversation still shows "sí" once and no "no"

  Scenario: Of two starts for one product sent before the case opens, only the first opens a case
    Given Juan has no case for a credit card
    When the app sends two credit card starts before the first is answered
    Then Juan has one credit card case with one decision
    And the second start is told the product already has a case

  Scenario: A customer who does not pre-qualify can ask a person to review it
    Given Mariana Mónica Acosta Rojas's credit card request ended as not pre-qualified by the policy
    When Mariana chooses "Pedir que una persona lo revise" on her certificate
    Then her case enters the review queue with reason "customer_requested_human"
    And the assistant tells her "Pediste que una persona atienda tu caso." and that a person from the bank will review her request
    And her certificate stays in the conversation above that notice

  Scenario: A result can be sent to a person only once
    Given Mariana asked a person to review her credit card result
    When the app asks for that review again
    Then her case is unchanged and has one review request

  Scenario: A pre-qualified result offers no review
    Given Juan pre-qualified for a credit card
    When Juan opens his certificate
    Then it offers no option to ask a person to review it

  Scenario: A no cannot go to a person while another case of its product is open
    Given Mariana's first credit card request ended as not pre-qualified by the policy
    And her second credit card case is open
    When Mariana opens the result of the first request
    Then it offers no option to ask a person to review it
    And a review requested for it anyway is refused because the product already has an open case
