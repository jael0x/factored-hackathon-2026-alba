Feature: Customer products
  As a bank customer
  I want to see my own products as the bank stores them
  So that I know what I already hold before I ask for credit

  Scenario: Juan sees his own products
    Given Juan Alberto Romero González is signed in
    When Juan opens his home page
    Then he sees these products:
      | product         | balance        |
      | savings account | 1,559.57 USD   |
      | mortgage        | 109,159.57 USD |
    And he sees no credit card

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
