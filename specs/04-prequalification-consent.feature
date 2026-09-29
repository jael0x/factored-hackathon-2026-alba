Feature: Pre-qualification consent
  As a bank customer
  I want to be asked before the bank checks whether I pre-qualify
  So that nothing is decided on my data until I agree

  Scenario: Naming a product gets a consent question before any decision
    Given Juan Alberto Romero González is signed in with no open case
    When Juan writes "quiero una tarjeta de crédito"
    Then the assistant asks whether to start the pre-qualification for a credit card
    And no certificate is shown
    And his case stays with the assistant

  Scenario: Confirming starts the pre-qualification
    Given the assistant asked Juan whether to start the pre-qualification for a credit card
    When Juan writes "sí"
    Then Juan sees a certificate for a credit card

  Scenario: Declining leaves the case open without a decision
    Given the assistant asked Juan whether to start the pre-qualification for a credit card
    When Juan writes "no, gracias"
    Then the assistant replies in the thread
    And no certificate is shown
    And his case stays with the assistant

  Scenario: A new request after a decline asks for consent again
    Given Juan declined the pre-qualification for a credit card
    When Juan writes "mejor sí quiero la tarjeta de crédito"
    Then the assistant asks whether to start the pre-qualification for a credit card

  Scenario: A confirmation that names no product gets asked which product
    Given Juan is signed in with no open case
    When Juan writes "sí, quiero precalificar"
    Then the assistant asks whether he wants a credit card or a personal loan
    And no certificate is shown
