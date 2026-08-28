if vim.g.loaded_gradebook then
  return
end
vim.g.loaded_gradebook = true

vim.api.nvim_create_user_command('Gradebook', function()
  require('gradebook').scan()
end, { desc = 'Scan the project with gradebook' })

vim.api.nvim_create_user_command('GradebookReport', function()
  require('gradebook').report()
end, { desc = 'Show the gradebook score report' })
