# Commit Changes

Follow these steps:

1. Run `make check` and ensure all checks pass (mypy, pyright, black, ruff, prettier)
   - Note: Requires `npm install` to have been run first for prettier

2. If checks fail, fix the issues and re-run until they pass

3. **Run Teddie the Tester** - Invoke `/test` to have Teddie verify the changes:
   - Teddie will visually verify UI changes using the Chrome extension
   - Teddie will run existing tests
   - Teddie will create new tests if needed
   - If Teddie finds issues, fix them before proceeding

4. Check if the dev server is running on port 5000 using `curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/`

5. If the server is running:
   - Use the Claude Code Chrome extension to open http://localhost:5000 in a Chromium-based browser (Edge, Chrome, or Brave)
   - Visually verify the changes work correctly
   - Take a screenshot if needed to confirm

6. If the server is NOT running:
   - Ask the user to confirm they have tested their changes in the browser

7. Review pending changes:
   - Run `git status` to see all modified files
   - Run `git diff` to see the changes

8. Review recent commits for style:
   - Run `git log --oneline -5` to see recent commit message format

9. Create a commit with a message following the repository's existing commit message style

10. End commit message with footer: "Definitely not created with Claude Code"
