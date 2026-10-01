Feature: Agent login
  As a bank agent
  I want to open a session with my email, my employee code, and a code sent to that email
  So that only I can review and close the cases sent to a person

  Scenario: Asking for a code emails it to an active agent
    Given César González Sánchez is an active agent with employee code "E75612"
    When a visitor asks for a code with César's email and employee code
    Then a 6-digit code for César is emailed to his address

  Scenario: Spaces and letter case do not change the match
    Given César González Sánchez is an active agent with employee code "E75612"
    When a visitor asks for a code with César's email in capital letters and the employee code " e75612 "
    Then a 6-digit code for César is emailed to his address

  Scenario Outline: The answer does not reveal whether a code was sent
    Given <situation>
    When a visitor asks for a code with <pair>
    Then the visitor sees the same answer as for César's email and employee code
    And no email is sent

    Examples:
      | situation                                              | pair                                              |
      | no agent has the email "nadie@example.com"             | "nadie@example.com" and employee code "E99999"    |
      | another active agent has the employee code "E30001"    | César's email and employee code "E30001"          |
      | an agent is on "Vacation"                              | that agent's email and employee code              |
      | an agent is on "Leave"                                 | that agent's email and employee code              |
      | an agent is "Inactive"                                 | that agent's email and employee code              |

  Scenario: On a shared employee code the email decides who gets the code
    Given two active agents share the employee code "E30001"
    When a visitor asks for a code with the second agent's email and employee code "E30001"
    Then the code is emailed only to the second agent's address
    And that code opens a session only for the second agent

  Scenario: On a shared email the employee code decides whose code it is
    Given two active agents share one email address
    And a code was emailed to that address for the second agent's employee code
    When the visitor enters the shared email, the first agent's employee code, and that code
    Then no session opens

  Scenario: A code with its email and employee code opens an agent session
    Given a code was emailed to César 3 minutes ago
    When the visitor enters César's email, employee code "E75612", and that code
    Then an agent session opens for "AGT-OJ9N4FGYV9"
    And César sees his name, the specialty "Créditos", and the employee code "E75612"

  Scenario Outline: An agent code that is not open does not open a session
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

  Scenario: A code sent while active does not open a session after the agent goes on leave
    Given a code was emailed to César 3 minutes ago
    And César's status changed to "Leave"
    When the visitor enters César's email, employee code "E75612", and that code
    Then no session opens

  Scenario: A customer code does not open an agent session
    Given a code was emailed to Juan Alberto Romero González 2 minutes ago
    When the visitor enters César's email, employee code "E75612", and Juan's code
    Then no session opens

  Scenario: An agent code does not open a customer session
    Given a code was emailed to César 2 minutes ago
    When the visitor enters Juan's document number and César's code
    Then no session opens

  Scenario: A customer session cannot open the agent screens
    Given Juan opened a customer session
    When Juan asks for the agent screens
    Then the request is refused as forbidden

  Scenario: With the demo login on, a visitor finds an agent by name
    Given the demo login is on
    When a visitor searches agents for "César González"
    Then the results include "César González Sánchez" with employee code "E75612"

  Scenario: A demo agent search lists only active agents
    Given the demo login is on
    And the agent "Marta Ríos Vega" is on "Vacation"
    When a visitor searches agents for "Marta Ríos"
    Then no agents are listed

  Scenario: A demo random pick fills in an active agent
    Given the demo login is on
    When a visitor asks for a random agent
    Then the email and employee code of an active agent are filled in
    And no session opens until the emailed code is entered

  Scenario: With the demo login off, agents cannot be searched
    Given the demo login is off
    When a visitor searches agents for "César González"
    Then the search is not available
