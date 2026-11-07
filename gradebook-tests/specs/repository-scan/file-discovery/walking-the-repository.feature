@domain:repository-scan @area:file-discovery @from:gradebook-tests/walking
Feature: Walking the repository
  Lets the operator grading a repository trust that the source and test counts reflect the project's own code, not dependencies, tool caches or build output.

  Background:
    Given the operator runs gradebook-tests over a repository with git history turned off

  @id:gradebook-tests.repository-scan.file-discovery.001 @rule:repository-scan.file-discovery.tool-directories-never-scanned @verified @source:gradebook-tests/gradebook_tests/walking.py#walk @test:gradebook-tests/tests/test_gradebook_tests.py#test_build_artifacts_are_not_counted_as_source
  Scenario Outline: Dependency, VCS and tool-cache folders are never scanned
    Given the repository has one source file "src/a.py"
    And the repository also has a code file "<folder>/dep/index.js"
    When the operator grades the repository
    Then the report counts 1 source file
    And nothing under "<folder>" appears in the counts or findings

    Examples:
      | folder       |
      | node_modules |
      | vendor       |
      | .venv        |
      | third_party  |
      | .git         |

  @id:gradebook-tests.repository-scan.file-discovery.002 @rule:repository-scan.file-discovery.build-output-read-for-reports-only @verified @source:gradebook-tests/gradebook_tests/walking.py#walk @test:gradebook-tests/tests/test_gradebook_tests.py#test_build_artifacts_are_not_counted_as_source @test:gradebook-tests/tests/test_gradebook_tests.py#test_coverage_report_found_inside_artifact_dir
  Scenario Outline: Build and report folders are read for evidence but not counted as code
    Given the repository has one source file "src/a.js"
    And the repository has a file "<folder>/<file>"
    When the operator grades the repository
    Then the report counts 1 source file
    And a coverage report inside "<folder>" would still be read as measured coverage

    Examples:
      | folder   | file                  |
      | dist     | bundle.js             |
      | coverage | coverage-summary.json |
      | build    | generated.py          |
      | target   | Main.java             |

  @id:gradebook-tests.repository-scan.file-discovery.003 @rule:repository-scan.file-discovery.oversized-source-counted-without-lines @inferred @source:gradebook-tests/gradebook_tests/walking.py#read_text @questionable
  Scenario: A source file over 512 KiB counts as a source file but adds no lines
    Given the repository has a source file "src/huge.py" larger than 512 KiB
    When the operator grades the repository
    Then the report counts "src/huge.py" among the source files
    And none of its lines are added to the source line count
    And no message says the file was too large to read

  @id:gradebook-tests.repository-scan.file-discovery.004 @rule:repository-scan.file-discovery.oversized-test-file-ignored @inferred @source:gradebook-tests/gradebook_tests/walking.py#read_text @questionable
  Scenario: A test file over 512 KiB is left out of the test counts entirely
    Given the repository has a test file "tests/test_huge.py" larger than 512 KiB
    When the operator grades the repository
    Then the report does not count "tests/test_huge.py" as a test file
    And none of its test cases are counted
    And no message says the file was skipped

  @id:gradebook-tests.repository-scan.file-discovery.005 @rule:repository-scan.file-discovery.unknown-file-types-not-counted @inferred @source:gradebook-tests/gradebook_tests/walking.py#language_of
  Scenario Outline: Files in no recognised language are not counted as source or tests
    Given the repository has one source file "src/a.py"
    And the repository also has a file "<file>"
    When the operator grades the repository
    Then the report counts 1 source file

    Examples:
      | file             |
      | README.md        |
      | docs/diagram.png |
      | Makefile         |
