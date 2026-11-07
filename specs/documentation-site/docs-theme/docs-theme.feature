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

  @id:documentation-site.docs-theme.002 @rule:docs.theme.shared-accent-palette @inferred @source:docs/stylesheets/extra.css#:root
  Scenario: The splash page and the rendered docs show the same accent colours
    Given the site accent pair is cyan #22d3ee and indigo #6366f1
    When a reader moves from the splash page to the rendered documentation
    Then the hero title on the splash page and on the docs home page is painted in a cyan-to-indigo gradient
    And primary buttons on both pages use a cyan-to-indigo gradient
    And the documentation's primary colour is indigo while its header and tabs sit on the page background

  @id:documentation-site.docs-theme.003 @rule:docs.theme.legible-links-per-scheme @inferred @source:docs/stylesheets/extra.css#[data-md-color-scheme="slate"]
  Scenario Outline: Links stay legible in both light and dark mode
    Given the reader has chosen the <scheme> colour scheme
    When the reader views a documentation page
    Then links are shown in <link_colour>
    And the page background is <background>

    Examples:
      | scheme | link_colour    | background                                   |
      | light  | indigo #6366f1 | the default white ground                     |
      | dark   | cyan #22d3ee   | near-black #0b0f1a, header and tabs included |

  @id:documentation-site.docs-theme.004 @rule:docs.theme.no-borrowed-logo @inferred @source:docs/stylesheets/extra.css#.md-header__button.md-logo
  Scenario: The documentation header shows no stand-in logo
    Given the project has no logo configured
    When a reader opens any documentation page
    Then the header shows the site title without a logo icon
    And the navigation drawer title shows no logo icon
