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

  Scenario: The referral notice tells the customer why a person will review
    Given Alicia's credit card request was referred by rule "R05"
    When Alicia reads her thread
    Then she reads "Tu historial crediticio necesita una revisión adicional." before the notice that a person will review her case
    And the notice does not mention her credit score
    And the notice does not say whether she pre-qualifies

  Scenario: A customer who already holds the product is told so
    Given Rodrigo Pérez Luna holds an active credit card
    When Rodrigo starts a credit card request from his home
    Then his case enters the review queue with reason "policy_refer"
    And he reads "Ya tienes una tarjeta de crédito con nosotros." before the notice that a person will review his case

  Scenario Outline: Every other handoff tells the customer why
    Given Juliana Castro Gómez was asked for her monthly income in her credit card case
    When Juliana writes "<message>" in that case
    Then she reads "<reason>" before the notice that a person will review her case

    Examples:
      | message                       | reason                                                     |
      | quiero hablar con una persona | Pediste que una persona atienda tu caso.                   |
      | quiero una hipoteca nueva     | Tu mensaje pide algo que no puedo resolver en este chat.   |
      | I want a credit card          | Por ahora solo puedo leer mensajes en español o portugués. |

  Scenario: The assistant stops replying once a person has the case
    Given Alicia's case is in the review queue
    When Alicia writes "¿ya revisaron mi caso?"
    Then her message is saved in the thread
    And the assistant does not reply

  Scenario: A message sent while the case is being handed off does not reach the model
    Given Juan wrote "quiero hablar con una persona"
    And his case has not reached the review queue yet
    When Juan writes "sí"
    Then his case enters the review queue with reason "customer_requested_human"
    And the assistant does not reply to "sí"

  Scenario Outline: A request the assistant should not handle goes to a person
    Given Juliana Castro Gómez was asked for her monthly income in her credit card case
    When Juliana writes "<message>" in that case
    Then her case enters the review queue with reason "<reason>"
    And no certificate is shown

    Examples:
      | message                        | reason                   |
      | quiero hablar con una persona  | customer_requested_human |
      | quiero una hipoteca nueva      | out_of_scope             |
      | je voudrais une carte bancaire | language_unsupported     |
      | I want a credit card           | language_unsupported     |

  Scenario: A message in another language that names no product is not asked which product
    Given Juliana Castro Gómez was asked for her monthly income in her credit card case
    When Juliana writes "I earn 3,000 a month" in that case
    Then her case enters the review queue with reason "language_unsupported"
    And the assistant does not ask which product she wants

  Scenario: A reply that states an outcome is withheld
    Given the assistant drafts a reply to Juan that says he "precalifica"
    When the reply is checked before it is shown
    Then Juan does not see that reply
    And his case enters the review queue with reason "reply_forbidden"

  Scenario: Repeated model failures send the case to a person
    Given the language model is unavailable
    When Juan writes "quiero una tarjeta de crédito"
    Then after three failed attempts his case enters the review queue with reason "tool_failed"

  Scenario: A technical failure tells the customer what happened
    Given Juan's message failed three times because the language model is unavailable
    When Juan reads his thread
    Then he reads "Tuvimos un problema técnico al procesar tu solicitud." before the notice that a person will review his case
