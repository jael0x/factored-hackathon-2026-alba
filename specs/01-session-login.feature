Feature: Session login
  As a bank customer
  I want to open a session with my document number and a code sent to my email
  So that only I can see and act on my own case

  Scenario: Asking for a code emails it to the address on file
    Given Juan Alberto Romero González has an email on file
    When a visitor asks for a code with Juan's document number
    Then a 6-digit code for Juan is emailed to his address on file

  Scenario Outline: The answer does not reveal whether a code was sent
    Given <situation>
    When a visitor asks for a code with <document>
    Then the visitor sees the same answer as for Juan's document number
    And no email is sent

    Examples:
      | situation                                    | document                        |
      | no customer has the document number 00000000 | the document number "00000000"  |
      | a customer has no email on file              | that customer's document number |

  Scenario: A code with its document number opens a session
    Given a code was emailed to Juan 3 minutes ago
    When the visitor enters Juan's document number and that code
    Then a customer session opens for "CLI-9EDEKZ8OUNUR"
    And the visitor sees Juan's products

  Scenario: A code older than 10 minutes does not open a session
    Given a code was emailed to Juan 11 minutes ago
    When the visitor enters Juan's document number and that code
    Then no session opens

  Scenario: A code entered with another customer's document number does not open a session
    Given a code was emailed to Juan 3 minutes ago
    When the visitor enters Alicia Mariana Parra Álvarez's document number and Juan's code
    Then no session opens

  Scenario: A document number without a code does not open a session
    Given a visitor knows Juan's document number
    When the visitor tries to open a session with that document number and no code
    Then no session opens

  Scenario: Five wrong codes spend the code
    Given a code was emailed to Juan 3 minutes ago
    And the visitor entered a wrong code 5 times with Juan's document number
    When the visitor enters the code that was emailed
    Then no session opens

  Scenario: A new code replaces the unused one
    Given a code was emailed to Juan 3 minutes ago
    And a second code was emailed to Juan 1 minute ago
    When the visitor enters Juan's document number and the first code
    Then no session opens

  Scenario: A used code does not open a second session
    Given Juan opened a session with a code 2 minutes ago
    When the visitor enters Juan's document number and the same code again
    Then no session opens

  Scenario: An expired session is not renewed
    Given Juan opened a session 16 minutes ago
    When Juan opens his case
    Then Juan sees that his session ended
    And no new session opens for him

  Scenario Outline: With the demo login on, a visitor finds a customer by name or customer id
    Given the demo login is on
    When a visitor searches customers for "<query>"
    Then the results include "<customer>"

    Examples:
      | query            | customer                     |
      | Juliana Castro   | Juliana Castro Gómez         |
      | CLI-440CO5FZIY6A | Alicia Mariana Parra Álvarez |

  Scenario: A demo search lists at most 20 customers
    Given the demo login is on
    And more than 20 customers have the last name "González"
    When a visitor searches customers for "González"
    Then 20 customers are listed

  Scenario: A demo random pick fills in a customer who can receive a code
    Given the demo login is on
    When a visitor asks for a random customer
    Then the document number of a customer with an email on file is filled in
    And no session opens until the emailed code is entered

  Scenario: With the demo login off, customers cannot be searched
    Given the demo login is off
    When a visitor searches customers for "Juliana Castro"
    Then the search is not available
