Feature: Language switch
  As a bank customer or consultant
  I want to read Alba in Spanish or Portuguese
  So that I understand every screen, email, and answer in my own language

  Scenario: A first visit follows the browser's language
    Given a visitor's browser prefers Portuguese
    And the visitor has never chosen a language on Alba
    When the visitor opens the customer login
    Then the title reads "Entre na sua conta"
    And Portuguese is the chosen language in the switch

  Scenario: A browser in another language gets Spanish
    Given a visitor's browser prefers English
    And the visitor has never chosen a language on Alba
    When the visitor opens the customer login
    Then the title reads "Entra a tu cuenta"

  Scenario: The chosen language is kept for the next visit
    Given a visitor whose browser prefers Spanish chose Portuguese on the customer login
    When the visitor comes back to the customer login the next day
    Then the title reads "Entre na sua conta"

  Scenario: A browser that blocks site storage still switches the language
    Given a visitor whose browser prefers Spanish and blocks site storage
    When the visitor chooses Portuguese on the customer login
    Then the title reads "Entre na sua conta"
    And after a reload the title reads "Entra a tu cuenta"

  Scenario: Changing the language keeps the visitor on the same screen
    Given Juan Alberto Romero González is reading his home page in Spanish
    When Juan chooses Portuguese in the switch
    Then the greeting reads "Olá, Juan Alberto"
    And Juan is still signed in on his home page

  Scenario Outline: Product names and statuses follow the chosen language
    Given Juan Alberto Romero González is signed in
    And the chosen language is <language>
    When Juan opens his home page
    Then his savings account ending in 5725 reads "<name>" with the status "<status>"

    Examples:
      | language   | name             | status |
      | Spanish    | Cuenta de ahorro | Activa |
      | Portuguese | Conta poupança   | Ativa  |

  Scenario: A status agrees with the gender the language gives the product
    Given a customer holds an active "Tarjeta Crédito"
    When the customer reads the home page in Portuguese
    Then the card reads "Cartão de crédito" with the status "Ativo"

  Scenario: Amounts keep one format in every language
    Given Juan Alberto Romero González is signed in
    And the chosen language is Portuguese
    When Juan opens his home page
    Then his savings balance reads "1,559.57 USD"

  Scenario Outline: The customer's login code email is written in the chosen language
    Given the chosen language is <language>
    When a visitor asks for a code with Juan's document number
    Then the email to Juan's address has the subject "<subject>"

    Examples:
      | language   | subject           |
      | Spanish    | Tu código de Alba |
      | Portuguese | Seu código Alba   |

  Scenario: A consultant's login code email is written in the chosen language
    Given the chosen language is Portuguese
    When a visitor asks for a code with César González Sánchez's email and employee code
    Then the email to César's address has the subject "Seu código Alba"

  Scenario: The assistant answers in the chosen language, not the language typed
    Given Juan Alberto Romero González chose Portuguese in the language switch
    And Juan has no open case
    When Juan writes "quiero una tarjeta de crédito"
    Then the assistant asks him in Portuguese whether to start the pre-qualification for a credit card

  Scenario: Changing the language during a case changes the next answer
    Given Juan wrote "quiero un crédito" with Spanish chosen
    And the assistant asked him in Spanish which product he means
    When Juan chooses Portuguese in the switch and writes "cartão de crédito"
    Then the assistant asks him in Portuguese whether to start the pre-qualification for a credit card

  Scenario: A message in English goes to a person whatever the switch says
    Given Juan Alberto Romero González chose Spanish in the language switch
    And Juan has no open case
    When Juan writes "I want a credit card"
    Then his case enters the review queue with reason "language_unsupported"

  Scenario: A code request without a language sends no email
    When a visitor asks for a code with Juan's document number and no language
    Then the request is rejected as invalid
    And no email is sent
