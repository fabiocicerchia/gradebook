@domain:command-line-ci @area:scoring-model-listing @from:gradebook-code/cli
Feature: Listing the code scoring model
  Shows an operator which dimensions make up the code score and what each one weighs, so they can read a score without the source.

  @id:gradebook-code.command-line-ci.scoring-model-listing.001 @rule:gradebook-code.cli.list-dimensions @verified @source:gradebook-code/gradebook_code/cli.py#main @test:gradebook-code/tests/test_gradebook_code.py#test_cli_lists_dimensions
  Scenario: The scoring model lists every dimension with its weight
    When the operator runs gradebook-code --list-dimensions
    Then each dimension is printed as its key, its weight in points and its title, e.g. "kiss        13 pts  Simplicity (KISS)"
    And a closing note says dimensions without evidence are left unscored and the remaining weights renormalise
    And no repository is scanned
    And the exit status is 0
