Feature: Product clarification
  As a bank customer
  I want the assistant to ask which product I mean
  So that I get a decision for the credit I actually want

  Scenario: An ambiguous request gets asked which product
    Given Juan Alberto Romero González is signed in with no open case
    When Juan writes "quiero un crédito"
    Then the assistant asks whether he wants a credit card or a personal loan
    And no certificate is shown
    And his case stays with the assistant

  Scenario: Naming the product after the question leads to a decision
    Given the assistant asked Juan whether he wants a credit card or a personal loan
    When Juan writes "una tarjeta de crédito"
    Then Juan sees a certificate for a credit card

  Scenario: A request that still names no product goes to a person
    Given the assistant already asked Juan once which product he wants
    When Juan writes "el crédito"
    Then his case enters the review queue with reason "out_of_scope"
    And no certificate is shown

  Scenario: A question about the products gets a reply without a decision
    Given Juan is signed in with no open case
    When Juan writes "¿qué productos de crédito ofrecen?"
    Then the assistant replies in the thread
    And no certificate is shown
    And his case stays with the assistant
