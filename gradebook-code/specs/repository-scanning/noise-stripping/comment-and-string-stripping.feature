@domain:repository-scanning @area:noise-stripping @from:gradebook-code/scanning
Feature: Ignoring comments and string literals when measuring code
  Serves anyone reading a gradebook-code report: words in comments, docstrings and strings must not inflate complexity, and every file:line must still point at the right line of the original file.

  Background:
    Given a repository containing source files in several languages

  @id:gradebook-code.repository-scanning.noise-stripping.001 @rule:scanning.noise.prose-adds-no-complexity @verified @source:gradebook-code/gradebook_code/scanning.py#strip_noise @test:gradebook-code/tests/test_gradebook_code.py#test_prose_does_not_add_branches @test:gradebook-code/tests/test_units.py#test_block_comments_are_blanked_across_lines @test:gradebook-code/tests/test_units.py#test_triple_quoted_strings_keep_their_delimiters @test:gradebook-code/tests/test_units.py#test_escaped_quotes_do_not_end_the_string
  Scenario Outline: Words in comments and strings do not count as branches
    Given a <language> function with no branches
    And its <prose> contains the words "if", "for", "while", "and" and "or"
    When the operator scores the repository with gradebook-code
    Then the function's complexity is reported as 1
    And the function is not flagged as a complex function

    Examples:
      | language   | prose                            |
      | Python     | docstring                        |
      | JavaScript | line comment and string literal  |
      | Go         | block comment and string literal |

  @id:gradebook-code.repository-scanning.noise-stripping.002 @rule:scanning.noise.line-numbers-preserved @verified @source:gradebook-code/gradebook_code/scanning.py#strip_noise @test:gradebook-code/tests/test_gradebook_code.py#test_strip_noise_preserves_offsets_and_lines
  Scenario: Reported line numbers match the original file even after comments and strings are ignored
    Given a file with a multi-line comment and string literals above a function that breaks a limit
    When the operator scores the repository with gradebook-code
    Then the red flag for that function cites the function's line in the original file

  @id:gradebook-code.repository-scanning.noise-stripping.003 @rule:scanning.noise.language-specific-markers @verified @source:gradebook-code/gradebook_code/scanning.py#strip_noise @test:gradebook-code/tests/test_units.py#test_slashes_are_code_where_hash_is_the_comment @test:gradebook-code/tests/test_units.py#test_lua_and_ruby_use_their_own_comment_markers @test:gradebook-code/tests/test_units.py#test_backticks_are_strings_only_where_the_language_says_so @test:gradebook-code/tests/test_gradebook_code.py#test_urls_are_not_read_as_comments @questionable
  Scenario Outline: What counts as a comment or a string follows each language's own syntax
    Given a <language> file containing <text>
    When the operator scores the repository with gradebook-code
    Then <text> is treated as <treated_as>

    Examples:
      | language   | text                 | treated_as              |
      | Python     | x = 4 // 2           | code (floor division)   |
      | Python     | # note               | a comment               |
      | Lua        | -- note              | a comment               |
      | Ruby       | =begin ... =end      | a comment               |
      | Go         | `if`                 | a string                |
      | Python     | `if`                 | code                    |
      | JavaScript | "http://example.com" | a string, not a comment |

  @id:gradebook-code.repository-scanning.noise-stripping.004 @rule:scanning.noise.unterminated-literals @verified @source:gradebook-code/gradebook_code/scanning.py#_comment_end @test:gradebook-code/tests/test_units.py#test_an_unterminated_string_stops_at_the_end_of_the_line @test:gradebook-code/tests/test_units.py#test_unterminated_block_comment_runs_to_the_end @questionable
  Scenario Outline: An unclosed string ends at its line, but an unclosed block comment hides the rest of the file
    Given a <language> file whose <literal> is never closed
    And code follows on later lines
    When the operator scores the repository with gradebook-code
    Then the code on later lines is <outcome>

    Examples:
      | language | literal          | outcome             |
      | Python   | string literal   | still measured      |
      | C        | /* block comment | not measured at all |
