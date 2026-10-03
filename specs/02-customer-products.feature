Feature: Customer products
  As a bank customer
  I want to see my own products as the bank stores them
  So that I know what I already hold before I ask for credit

  Scenario: Juan sees his own products
    Given Juan Alberto Romero González is signed in
    When Juan opens his home page
    Then he sees these products:
      | product              | number   | balance        | status |
      | Cuenta de ahorro     | ••••5725 | 1,559.57 USD   | Activa |
      | Préstamo hipotecario | ••••1597 | 109,159.57 USD | Activo |
    And none of them is a "Tarjeta de crédito"

  Scenario: Balances of customers in Mexico stay in USD
    Given Juliana Castro Gómez lives in Ciudad de México
    And her checking account balance is stored as 2,528.58 USD
    When Juliana opens her home page
    Then she sees her checking balance as 2,528.58 USD
    And the balance is not converted to MXN

  Scenario: Balances show the currency stored on the product
    Given Alicia Mariana Parra Álvarez has a checking account of 13,192,324.57 COP
    When Alicia opens her home page
    Then she sees her checking balance as 13,192,324.57 COP

  Scenario: A customer cannot see another customer's products
    Given Juan is signed in
    When Juan asks for the products of customer "CLI-440CO5FZIY6A"
    Then no product of Alicia is returned

  Scenario: A closed product is not shown
    Given Alicia Mariana Parra Álvarez has a savings account ending in 0665 whose status is "Closed"
    When Alicia opens her home page
    Then she does not see a product ending in 0665

  Scenario: A paid loan is not shown
    Given a customer has a "Préstamo Personal" with a balance of 0 and the status "Active"
    When that customer opens the home page
    Then the customer does not see that loan
    And the loan keeps the status "Active" in the bank's records

  Scenario: A credit card with a balance of zero is still shown
    Given a customer has a "Tarjeta Crédito" with a balance of 0.00 USD
    When that customer opens the home page
    Then the customer sees a "Tarjeta de crédito" with 0.00 USD

  Scenario: A customer without products is told there are none
    Given a customer holds no product at the bank
    When that customer opens the home page
    Then the customer reads "Todavía no tienes productos con nosotros."
