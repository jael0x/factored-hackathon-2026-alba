Feature: Data load
  As the team running the demo
  I want the stack to load the bank data by itself on start
  So that nobody runs SQL by hand and every customer can log in

  Scenario: The first start copies only the four source files
    Given the local data folder is empty
    And the AWS keys are set
    When the team starts the stack
    Then only these files are copied from the bucket:
      | file                     |
      | customers.csv            |
      | products.csv             |
      | daily_exchange_rates.csv |
      | service_agents.csv       |

  Scenario: Files already on disk are not copied again
    Given the four source files are already in the local data folder
    When the team starts the stack
    Then no file is copied from the bucket

  Scenario: Unchanged files are not loaded into the database again
    Given the database already holds a load of the same four files
    When the team starts the stack again
    Then the files are not loaded into the database again

  Scenario: A changed file is loaded again
    Given the database holds a load of the four source files
    And products.csv on disk has changed since that load
    When the team starts the stack again
    Then the read tables and the customer credit profiles are rebuilt from the changed file

  Scenario: A row count that differs from the snapshot stops the load
    Given customers.csv holds 149,999 rows instead of the expected 150,000
    When the team starts the stack
    Then the load fails its quality check
    And the application does not start

  Scenario: A product with no matching customer stops the load
    Given products.csv holds a product whose customer id is not in customers.csv
    When the team starts the stack
    Then the load fails its quality check
    And the application does not start

  Scenario: Missing keys and missing files stop the load with a named error
    Given the local data folder is empty
    And the AWS keys are not set
    When the team starts the stack
    Then the load stops with an error that names the missing AWS variables
    And the application does not start

  Scenario: Every customer gets one credit profile
    Given the source files hold 150,000 customers
    When the load finishes
    Then 150,000 customer credit profiles exist, one per customer

  Scenario: Missing scores and incomes stay empty
    Given 22,492 customers have no credit score in the source file
    And 30,033 customers have no income in the source file
    When the load finishes
    Then those customers keep an empty score or an empty income
    And the load does not fail

  Scenario: A missing balance loads as zero
    Given a product in the source file has no balance
    When the load finishes
    Then that product has a balance of 0
    And the load does not fail

  Scenario: The load report counts the customers without a score
    Given 22,492 customers have no credit score in the source file
    When the load finishes
    Then the load report shows 22,492 customers without a credit score
