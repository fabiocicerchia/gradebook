@domain:external-evidence @area:coverage-reports @from:gradebook-tests/coverage
Feature: Reading measured coverage reports
  Lets a team lead see the coverage their pipeline actually measured, overall and per file, from whatever report format their stack produces, rather than relying on declared intent.

  Background:
    Given the repository has source files and a test suite

  @id:gradebook-tests.external-evidence.coverage-reports.001 @rule:gradebook-tests.coverage.report-formats-yield-overall-percent @verified @source:gradebook-tests/gradebook_tests/coverage.py#measure_coverage @test:gradebook-tests/tests/test_gradebook_tests.py#test_parses_cobertura @test:gradebook-tests/tests/test_gradebook_tests.py#test_parses_lcov @test:gradebook-tests/tests/test_gradebook_tests.py#test_parses_jacoco @test:gradebook-tests/tests/test_gradebook_tests.py#test_parses_go_coverprofile @test:gradebook-tests/tests/test_gradebook_tests.py#test_parses_json_coverage_reports @test:gradebook-tests/tests/test_gradebook_tests.py#test_coverage_report_found_inside_artifact_dir @test:gradebook-tests/tests/test_gradebook_tests.py#test_measured_coverage_beats_declared_only
  Scenario Outline: A coverage report in a supported format gives the measured coverage
    Given the repository contains a coverage report named <report> with <content>
    When the operator grades the repository
    Then the measured coverage is <percent>%
    And the coverage source is the report's path

    Examples:
      | report                         | content                                                 | percent |
      | coverage.xml                   | a Cobertura line-rate of 0.8123                         | 81.2    |
      | lcov.info                      | 100 lines found, 75 lines hit                           | 75.0    |
      | jacoco.xml                     | a report-level LINE counter of 20 missed and 80 covered | 80.0    |
      | coverage.out                   | a Go profile with 4 of 10 statements executed           | 40.0    |
      | coverage.json                  | Python totals percent_covered 91.4                      | 91.4    |
      | coverage/coverage-summary.json | Istanbul total lines pct 88                             | 88.0    |

  @id:gradebook-tests.external-evidence.coverage-reports.002 @rule:gradebook-tests.coverage.unnamed-jacoco-recognised-by-content @inferred @source:gradebook-tests/gradebook_tests/coverage.py#measure_coverage
  Scenario: A JaCoCo report with a generic name is still read as JaCoCo
    Given the repository contains coverage.xml holding JaCoCo LINE counters and no line-rate attribute
    When the operator grades the repository
    Then the measured coverage is the covered share of the report-level LINE counter
    And the per-file coverage lists each JaCoCo source file

  @id:gradebook-tests.external-evidence.coverage-reports.003 @rule:gradebook-tests.coverage.unparseable-report-leaves-coverage-unmeasured @verified @source:gradebook-tests/gradebook_tests/coverage.py#measure_coverage @test:gradebook-tests/tests/test_gradebook_tests.py#test_parses_json_coverage_reports
  Scenario Outline: A coverage report that yields no percentage leaves coverage unmeasured
    Given the repository's only coverage report is <report> containing <content>
    When the operator grades the repository
    Then no measured coverage is recorded
    And no per-file coverage is reported

    Examples:
      | report        | content                             |
      | coverage.json | text that is not JSON               |
      | lcov.info     | records with zero lines found       |
      | coverage.xml  | no line-rate and no JaCoCo counters |

  @id:gradebook-tests.external-evidence.coverage-reports.005 @rule:gradebook-tests.coverage.per-file-by-base-name @verified @source:gradebook-tests/gradebook_tests/coverage.py#lcov_files @test:gradebook-tests/tests/test_gradebook_tests.py#test_per_file_coverage_parsers @questionable
  Scenario: Per-file coverage is reported by file name, without its folder
    Given the coverage report lists src/a.py at 50% and pkg/a.py at 90%
    When the operator grades the repository
    Then the per-file coverage has one entry, a.py
    And that entry holds whichever of the two the report listed last
