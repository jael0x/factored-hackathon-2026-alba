Feature: Handoff to a consultant
  As a bank customer
  I want borderline or unusual requests to reach a person
  So that the assistant never guesses on my behalf

  Scenario: A review-band score is referred to a person
    Given Alicia Mariana Parra Álvarez has a credit score of 615 and income on file
    And she holds no active credit card
    And the assistant asked Alicia whether to start the pre-qualification for a credit card
    When Alicia writes "sí"
    Then her case enters the review queue with reason "policy_refer"

  Scenario: The referral notice tells the customer a person will review
    Given Alicia's credit card request was referred
    When Alicia reads her thread
    Then she sees a notice that a person will review her case
    And the notice does not mention her credit score
    And the notice does not say whether she pre-qualifies

  Scenario: The assistant stops replying once a person has the case
    Given Alicia's case is in the review queue
    When Alicia writes "¿ya revisaron mi caso?"
    Then her message is saved in the thread
    And the assistant does not reply

  Scenario Outline: A request the assistant should not handle goes to a person
    Given Juan Alberto Romero González is signed in with no open case
    When Juan writes "<message>"
    Then his case enters the review queue with reason "<reason>"
    And no certificate is shown

    Examples:
      | message                       | reason                   |
      | quiero hablar con una persona | customer_requested_human |
      | quiero una hipoteca nueva     | out_of_scope             |
      | I would like a credit card    | language_unsupported     |

  Scenario: A message in another language that names no product is not asked which product
    Given Juan Alberto Romero González is signed in with no open case
    When Juan writes "I earn 3,000 a month"
    Then his case enters the review queue with reason "language_unsupported"
    And the assistant does not ask which product he wants

  Scenario: A reply that states an outcome is withheld
    Given the assistant drafts a reply to Juan that says he "precalifica"
    When the reply is checked before it is shown
    Then Juan does not see that reply
    And his case enters the review queue with reason "reply_forbidden"

  Scenario: Repeated model failures send the case to a person
    Given the language model is unavailable
    When Juan writes "quiero una tarjeta de crédito"
    Then after three failed attempts his case enters the review queue with reason "tool_failed"
