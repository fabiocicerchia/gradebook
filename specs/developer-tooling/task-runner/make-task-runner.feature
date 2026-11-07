@domain:developer-tooling @area:task-runner @from:gradebook/makefile
Feature: Running the repository's verbs from one entry point
  Contributors and operators get one discoverable set of make verbs for both tools, and a verb that cannot do its job says why instead of exiting quietly.

  Background:
    Given a checkout of the gradebook repository

  @id:developer-tooling.task-runner.001 @rule:tooling.make.bare-make-lists-verbs @inferred @source:Makefile#help
  Scenario: Running make with no verb lists every verb with its description
    When the contributor runs make with no verb
    Then a list of verbs is printed, one per line, each with its one-line description
    And the list includes help, setup, install, run, test, lint, format, analyze, build, clean and the four ext- verbs
    And nothing is installed, built or tested

  @id:developer-tooling.task-runner.002 @rule:tooling.make.run-tool-from-checkout @inferred @source:Makefile#run
  Scenario Outline: One tool can be run from the checkout without installing it
    Given neither tool is installed
    When the contributor runs the run verb with TOOL <tool> and ARGS <args>
    Then the <module> module is run from the <tool> folder with <args>
    And its output is what the installed <tool> command would print for <args>

    Examples:
      | tool                     | args              | module          |
      | (default) gradebook-code | (default) --help  | gradebook_code  |
      | gradebook-tests          | --list-dimensions | gradebook_tests |
      | gradebook-code           | --list-dimensions | gradebook_code  |

  @id:developer-tooling.task-runner.003 @rule:tooling.make.build-is-declared-no-op @inferred @source:Makefile#build
  Scenario: The build verb explains that there is nothing to build
    When the contributor runs the build verb
    Then it prints that there is nothing to build because both tools are pure-Python packages installed by make install
    And it points to make ext-build for the VS Code extension and to the README's Not applicable section
    And nothing is compiled or installed

  @id:developer-tooling.task-runner.004 @rule:tooling.make.missing-prerequisite-refused-with-guidance @inferred @source:Makefile#analyze
  Scenario Outline: A verb whose required tool is missing stops with guidance and a failing status
    Given <prerequisite> is not on the PATH
    When the operator runs the <verb> verb
    Then it prints <guidance>
    And it exits with status <status> without running the scan or the install

    Examples:
      | verb        | prerequisite | guidance                                                                                                              | status |
      | analyze     | trivy        | analyze needs trivy: https://trivy.dev/latest/getting-started/installation/                                           | 69     |
      | ext-install | the code CLI | the 'code' CLI is not on PATH, how to install it from VS Code, or to install the built .vsix from the Extensions view | 1      |

  @id:developer-tooling.task-runner.005 @rule:tooling.make.analyze-reports-high-and-critical @inferred @source:Makefile#analyze
  Scenario: The security scan reports only high and critical vulnerabilities, misconfigurations and secrets
    Given trivy is installed
    When the operator runs the analyze verb
    Then the whole working tree is scanned for vulnerabilities, misconfigurations and secrets
    And only findings of severity CRITICAL or HIGH are reported
