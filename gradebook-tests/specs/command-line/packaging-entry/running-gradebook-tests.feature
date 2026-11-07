@domain:command-line @area:packaging-entry @from:gradebook-tests/gradebook-tests
Feature: Running gradebook-tests
  Operators, CI jobs and editor plugins can start the test-suite grader as an installed command or as a Python module, and get the same results and exit status either way.

  Background:
    Given the gradebook-tests package is on the interpreter's path

  @id:gradebook-tests.command-line.packaging-entry.001 @rule:cli.entry.module-run-matches-console-script @inferred @source:gradebook-tests/gradebook_tests/__main__.py#main
  Scenario Outline: Running the grader as a Python module behaves like the gradebook-tests command
    Given a repository at /srv/repos/acme-shop
    When the operator runs "python3 -m gradebook_tests /srv/repos/acme-shop <options>"
    Then the output is the same as from "gradebook-tests /srv/repos/acme-shop <options>"
    And the process exit status is the same as the gradebook-tests command's

    Examples:
      | options           |
      |                   |
      | --format markdown |
      | --fail-under 60   |
