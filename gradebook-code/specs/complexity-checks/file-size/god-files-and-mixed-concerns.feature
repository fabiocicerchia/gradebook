@domain:complexity-checks @area:file-size @from:gradebook-code/collection
Feature: Flagging files that do too many jobs
  Points a maintainer at the files that have grown into whole subsystems or mix unrelated infrastructure, the first candidates to split.

  Background:
    Given a repository the operator wants to grade with gradebook-code

  @id:gradebook-code.complexity-checks.file-size.001 @rule:code.size.god-file-flagged @verified @source:gradebook-code/gradebook_code/collection.py#_name_and_size_tallies @test:gradebook-code/tests/test_gradebook_code.py#test_god_files_are_flagged
  Scenario Outline: A file over 400 lines or 20 functions is flagged as a god file
    Given the source file "src/everything.py" has <lines> lines and <functions> functions
    When the operator grades the repository
    Then <outcome>
    And a god-file red flag points at "src/everything.py:1" and states its lines, functions and classes

    Examples:
      | lines | functions | outcome                           |
      | 401   | 5         | the file is flagged as a god file |
      | 120   | 21        | the file is flagged as a god file |

  @id:gradebook-code.complexity-checks.file-size.002 @rule:code.size.mixed-concerns-flagged @verified @source:gradebook-code/gradebook_code/collection.py#_accumulate @test:gradebook-code/tests/test_gradebook_code.py#test_mixed_concerns_are_flagged
  Scenario: A file touching three or more kinds of infrastructure is flagged for mixing concerns
    Given the source file "src/all.py" uses a database driver, an HTTP client and a hashing library
    When the operator grades the repository
    Then a mixed-concerns red flag points at "src/all.py:1"
    And its message reads "touches crypto, database, http in one file"
