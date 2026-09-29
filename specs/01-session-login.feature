Feature: Session login
  As a bank customer or credit agent
  I want to open a session with a one-time code
  So that only I can see and act on my own case

  Scenario Outline: A visitor finds a customer by name or customer id
    When a visitor searches customers for "<query>"
    Then the results include "<customer>"

    Examples:
      | query            | customer                     |
      | Juliana Castro   | Juliana Castro Gómez         |
      | CLI-440CO5FZIY6A | Alicia Mariana Parra Álvarez |

  Scenario: A customer search lists at most 20 customers
    Given more than 20 customers have the last name "González"
    When a visitor searches customers for "González"
    Then 20 customers are listed

  Scenario: A random pick issues a code for an existing customer
    When a visitor asks for a random customer
    Then a code is issued for one of the 150,000 customers

  Scenario: The demo inbox shows the one-time code
    Given the demo inbox is enabled
    When a visitor requests a code for "CLI-9EDEKZ8OUNUR"
    Then a 6-digit code for Juan Alberto Romero González appears in the demo inbox

  Scenario: A valid code opens a session for its customer
    Given a code was issued for "CLI-9EDEKZ8OUNUR" 3 minutes ago
    When the visitor enters that code
    Then a customer session opens for "CLI-9EDEKZ8OUNUR"
    And the visitor sees Juan's products

  Scenario: A code older than 10 minutes does not open a session
    Given a code was issued for "CLI-9EDEKZ8OUNUR" 11 minutes ago
    When the visitor enters that code
    Then no session opens

  Scenario: A customer id without a code does not open a session
    Given a visitor knows the customer id "CLI-9EDEKZ8OUNUR"
    When the visitor tries to open a session with that id and no code
    Then no session opens

  Scenario: An expired session is not renewed
    Given Juan opened a session 16 minutes ago
    When Juan opens his case
    Then Juan sees that his session ended
    And no new session opens for him

  Scenario: A visitor finds an agent by name
    When a visitor searches agents for "César González"
    Then the results include "César González Sánchez" with employee code "E75612"
