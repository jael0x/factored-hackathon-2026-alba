Feature: Cases per product
  As a bank customer
  I want one conversation for each product I ask about
  So that I can continue a request or see its result without starting over

  Scenario: An open case turns its product row into a way back to it
    Given Juliana Castro Gómez was asked for her monthly income in her credit card case
    When Juliana opens her home page
    Then the "Tarjeta de crédito" row reads "Continuar la conversación"
    And choosing it opens that case

  Scenario: An ended case turns its product row into its result
    Given Juan Alberto Romero González pre-qualified for a credit card
    When Juan opens his home page
    Then the "Tarjeta de crédito" row reads "Ver resultado"
    And choosing it opens his certificate

  Scenario: Each product has its own case
    Given Juliana has an open credit card case
    When Juliana starts a personal loan request from her home
    Then Juliana has two open cases, one for each product

  Scenario: A product that already has an open case cannot start another
    Given Juliana has an open credit card case
    When the app sends a new credit card start for Juliana
    Then the start is refused because the case is already open

  Scenario: A message stays in the case it was written in
    Given Juliana has open cases for a credit card and a personal loan
    When Juliana writes "gano 45,000 pesos al mes" in the credit card case
    Then the message appears only in the credit card case

  Scenario: Naming the other product switches the case and asks consent in the thread
    Given Juliana's credit card case is open and she has no personal loan case
    When Juliana writes "quiero un préstamo personal" in that case
    Then the case is now about a personal loan
    And the assistant asks whether to start the pre-qualification for a personal loan

  Scenario: Naming a product that has its own open case points to that case
    Given Juliana has open cases for a credit card and a personal loan
    When Juliana writes "quiero un préstamo personal" in the credit card case
    Then the assistant says she already has an open conversation about a personal loan
    And the credit card case keeps its product
