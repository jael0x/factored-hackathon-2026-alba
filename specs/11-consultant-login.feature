Feature: Consultant login
  As a bank consultant
  I want to open a session with my email, my employee code, and a code sent to that email
  So that only I can review and close the cases sent to a person

  Scenario: Asking for a code emails it to an active consultant
    Given César González Sánchez is an active consultant with employee code "E75612"
    When a visitor asks for a code with César's email and employee code
    Then a 6-digit code for César is emailed to his address

  Scenario: Spaces and letter case do not change the match
    Given César González Sánchez is an active consultant with employee code "E75612"
    When a visitor asks for a code with César's email in capital letters and the employee code " e75612 "
    Then a 6-digit code for César is emailed to his address

  Scenario Outline: The answer does not reveal whether a code was sent
    Given <situation>
    When a visitor asks for a code with <pair>
    Then the visitor sees the same answer as for César's email and employee code
    And no email is sent

    Examples:
      | situation                                                | pair                                           |
      | no consultant has the email "nadie@example.com"          | "nadie@example.com" and employee code "E99999" |
      | another active consultant has the employee code "E30001" | César's email and employee code "E30001"       |
      | a consultant is on "Vacation"                            | that consultant's email and employee code      |
      | a consultant is on "Leave"                               | that consultant's email and employee code      |
      | a consultant is "Inactive"                               | that consultant's email and employee code      |

  Scenario: On a shared employee code the email decides who gets the code
    Given two active consultants share the employee code "E30001"
    When a visitor asks for a code with the second consultant's email and employee code "E30001"
    Then the code is emailed only to the second consultant's address
    And that code opens a session only for the second consultant

  Scenario: On a shared email the employee code decides whose code it is
    Given two active consultants share one email address
    And a code was emailed to that address for the second consultant's employee code
    When the visitor enters the shared email, the first consultant's employee code, and that code
    Then no session opens

  Scenario: A code with its email and employee code opens a consultant session
    Given a code was emailed to César 3 minutes ago
    When the visitor enters César's email, employee code "E75612", and that code
    Then a consultant session opens for "AGT-OJ9N4FGYV9"
    And César sees his name, the specialty "Créditos", and the employee code "E75612"

  Scenario Outline: A consultant code that is not open does not open a session
    Given a code was emailed to César 3 minutes ago
    And <condition>
    When the visitor enters César's email, employee code "E75612", and that code
    Then no session opens

    Examples:
      | condition                                       |
      | the code is now 11 minutes old                  |
      | a wrong code was entered 5 times                |
      | a second code was emailed to César 1 minute ago |
      | that code already opened a session              |

  Scenario: A code sent while active does not open a session after the consultant goes on leave
    Given a code was emailed to César 3 minutes ago
    And César's status changed to "Leave"
    When the visitor enters César's email, employee code "E75612", and that code
    Then no session opens

  Scenario: A customer code does not open a consultant session
    Given a code was emailed to Juan Alberto Romero González 2 minutes ago
    When the visitor enters César's email, employee code "E75612", and Juan's code
    Then no session opens

  Scenario: A consultant code does not open a customer session
    Given a code was emailed to César 2 minutes ago
    When the visitor enters Juan's document number and César's code
    Then no session opens

  Scenario: A customer session cannot open the consultant screens
    Given Juan opened a customer session
    When Juan asks for the consultant screens
    Then the request is refused as forbidden

  Scenario: With the demo login on, a visitor finds a consultant by name
    Given the demo login is on
    When a visitor searches consultants for "César González"
    Then the results include "César González Sánchez" with employee code "E75612"

  Scenario: A demo consultant search lists only active consultants
    Given the demo login is on
    And the consultant "Marta Ríos Vega" is on "Vacation"
    When a visitor searches consultants for "Marta Ríos"
    Then no consultants are listed

  Scenario: A demo random pick fills in an active consultant
    Given the demo login is on
    When a visitor asks for a random consultant
    Then the email and employee code of an active consultant are filled in
    And no session opens until the emailed code is entered

  Scenario: With the demo login off, consultants cannot be searched
    Given the demo login is off
    When a visitor searches consultants for "César González"
    Then the search is not available

  Scenario: With the demo login on, the code step fills the code sent to the email typed
    Given the demo login is on
    And a visitor asked for a code with César's email and employee code
    When the code step opens
    Then the code field holds the code emailed to César's address in the test mailbox
    And no session opens until the visitor presses "Abrir sesión"
