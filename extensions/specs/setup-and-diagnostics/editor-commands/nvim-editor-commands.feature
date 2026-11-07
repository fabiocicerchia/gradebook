@domain:setup-and-diagnostics @area:editor-commands @from:nvim/plugin
Feature: Running gradebook from Neovim commands
  Gives a Neovim user two commands to scan the project and open the score report on demand, without leaving the editor.

  Background:
    Given the gradebook plugin is installed in Neovim

  @id:extensions.setup-and-diagnostics.editor-commands.001 @rule:editor.commands.nvim-scan-and-report @inferred @source:extensions/nvim/plugin/gradebook.lua#Gradebook
  Scenario Outline: The Neovim commands scan the project and open the score report
    Given a project is open in Neovim
    When the user runs the <command> command
    Then <outcome>

    Examples:
      | command          | outcome                                                          |
      | :Gradebook       | a gradebook scan of the project starts with the configured tools |
      | :GradebookReport | the score report opens in a floating window                      |
