Feature: Income request
  As a bank customer whose income is not on file
  I want the assistant to ask for my monthly income
  So that my request can be decided without waiting for a person

  Scenario: A customer with no income on file is asked for it
    Given Juliana Castro Gómez has no income on file and a credit score of 714
    When Juliana writes "quiero una tarjeta de crédito"
    Then the assistant asks for her monthly income
    And no certificate is shown
    And her case stays with the assistant

  Scenario: A stated income lets the decision continue
    Given the assistant asked Juliana for her monthly income for a credit card
    When Juliana writes "gano 45,000 pesos al mes"
    Then Juliana sees a certificate that says she pre-qualifies for a credit card
    And her case never enters the review queue

  Scenario: A stated income is read in the country's currency and marked as self-declared
    Given the assistant asked Juliana for her monthly income for a credit card
    When Juliana writes "gano 45,000 pesos al mes"
    Then the decision records her income as 45,000 MXN
    And the decision marks that income as self-declared

  Scenario: A stated income is not saved to the customer record
    Given Juliana pre-qualified for a credit card with a stated income of 45,000 MXN
    When Juliana later asks to pre-qualify for a personal loan
    Then the assistant asks for her monthly income again

  Scenario: An income stated before naming a product gets asked which product
    Given Juliana is signed in with no open case
    When Juliana writes "gano 45,000 pesos al mes"
    Then the assistant asks whether she wants a credit card or a personal loan
    And no certificate is shown

  Scenario: The income on file wins over a typed amount
    Given Juan Alberto Romero González has an income of 306,753.45 MXN on file
    When Juan writes "quiero una tarjeta de crédito, gano 10,000 pesos al mes"
    Then his decision uses the income of 306,753.45 MXN
