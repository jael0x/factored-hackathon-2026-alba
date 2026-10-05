Feature: Pre-qualification consent
  As a bank customer
  I want to be asked before the bank checks whether I pre-qualify
  So that nothing is decided on my data until I agree

  A case starts from a product on the home, and its dialog is the consent (PLAN.md D24). A consent question in
  the thread comes only when a message switches the case to the other product. Scenarios that begin with no case
  describe the engine; the screen reaches them only inside a case.

  Scenario: Choosing a product on the home asks for consent in a dialog
    Given Juan Alberto Romero González is on his home page with no case for a credit card
    When Juan chooses "Tarjeta de crédito" under "Preguntar por"
    Then a dialog says Alba will check whether he pre-qualifies for a credit card under the bank's policy
    And the dialog says the check is a simulation that opens no product
    And no case opens until Juan presses "Empezar"

  Scenario Outline: Starting from the dialog decides without asking again
    Given Juan Alberto Romero González is on his home page in <language> with no case for a credit card
    When Juan chooses "<row>" and presses "<begin>" in the dialog
    Then his message "<message>" opens his case
    And Juan sees his certificate for a credit card in <language>
    And the assistant does not ask whether to start the pre-qualification

    Examples:
      | language   | row                | begin   | message                       |
      | Spanish    | Tarjeta de crédito | Empezar | Quiero una tarjeta de crédito |
      | Portuguese | Cartão de crédito  | Começar | Quero um cartão de crédito    |

  Scenario: Cancelling the dialog opens no case
    Given the dialog for a credit card is open on Juan's home page
    When Juan presses "Cancelar"
    Then the dialog closes
    And Juan has no case for a credit card

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

  Scenario: An income stated instead of answering the consent question asks for consent again
    Given Juliana Castro Gómez has no income on file
    And the assistant asked Juliana whether to start the pre-qualification for a credit card
    When Juliana writes "gano 45,000 pesos al mes"
    Then the assistant asks whether to start the pre-qualification for a credit card
    And no certificate is shown
    And her case stays with the assistant

  Scenario: A yes that states an income uses that income
    Given Juliana Castro Gómez has no income on file and a credit score of 714
    And the assistant asked Juliana whether to start the pre-qualification for a credit card
    When Juliana writes "sí, gano 45,000 pesos al mes"
    Then Juliana sees a certificate that says she pre-qualifies for a credit card
    And the decision marks that income as self-declared

  Scenario: A confirmation that names no product gets asked which product
    Given Juan is signed in with no open case
    When Juan writes "sí, quiero precalificar"
    Then the assistant asks whether he wants a credit card or a personal loan
    And no certificate is shown
