@domain:documentation-site @area:docs-theme @from:docs/stylesheets
Feature: Branding the documentation site
  Gives readers of the gradebook docs and splash page one consistent, offline-safe look, so the site reads as one product in both light and dark mode.

  Background:
    Given the gradebook documentation site and its splash page are published

  @id:documentation-site.docs-theme.001 @rule:docs.theme.no-external-requests @inferred @source:docs/stylesheets/extra.css#:root
  Scenario: The documentation renders without fetching fonts or assets from the network
    Given a reader whose browser blocks every third-party host
    When the reader opens a documentation page
    Then the text is set in the operating system's own sans-serif typeface
    And code is set in the operating system's own monospace typeface
    And no web font, CDN asset or analytics script is requested
