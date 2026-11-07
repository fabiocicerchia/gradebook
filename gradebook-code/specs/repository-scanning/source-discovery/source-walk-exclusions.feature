@domain:repository-scanning @area:source-discovery @from:gradebook-code/metrics
Feature: Choosing which files the scan reads
  Lets an operator point the tool at a real checkout and get a grade for the team's own code, not for vendored packages, build output or oversized blobs.

  Background:
    Given the operator runs gradebook-code over a repository

  @id:gradebook-code.repository-scanning.source-discovery.001 @rule:gradebook-code.source-discovery.vendored-and-build-dirs-ignored @verified @source:gradebook-code/gradebook_code/metrics.py#walk @test:gradebook-code/tests/test_gradebook_code.py#test_only_source_files_are_counted @questionable
  Scenario Outline: Vendored, tool and build-output directories are not scanned
    Given the repository has source in src/
    And it also has source under <directory>/
    When the operator scores the repository
    Then only the files in src/ are counted
    And no finding points into <directory>/

    Examples:
      | directory    | kind                  |
      | node_modules | vendored dependencies |
      | vendor       | vendored dependencies |
      | .venv        | tool environment      |
      | migrations   | schema migrations     |
      | dist         | build output          |
      | coverage     | build output          |
      | generated    | generated code        |
      | proto        | generated code        |

  @id:gradebook-code.repository-scanning.source-discovery.002 @rule:gradebook-code.source-discovery.oversized-files-ignored @inferred @source:gradebook-code/gradebook_code/metrics.py#read_text @questionable
  Scenario: Source files larger than 512 KiB are ignored without being reported
    Given the repository has a 600 KiB source file src/schema_dump.py
    And a small source file src/app.py
    When the operator scores the repository
    Then only src/app.py is counted as a source file
    And src/schema_dump.py is not counted among the generated files skipped
