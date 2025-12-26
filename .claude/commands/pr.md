# Create Pull Request

Follow these steps:

1. Run `make check` and ensure all checks pass
   - Note: Requires `npm install` to have been run first for prettier

2. Check if the dev server is running on port 5000 using `curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/`

3. If the server is running:
   - Use the Claude Code Chrome extension to open http://localhost:5000 in a Chromium-based browser (Edge, Chrome, or Brave)
   - Visually verify the changes work correctly
   - Take a screenshot if needed to confirm

4. If the server is NOT running:
   - Ask the user to confirm they have tested their changes in the browser

5. If there are uncommitted changes, run `/commit` first

6. If there are unpushed commits, push them first

7. Review what will be in the PR:
   - Run `git log origin/main..HEAD --oneline` to see commits
   - Run `git diff origin/main..HEAD --stat` to see changed files

8. Create a PR using `gh pr create` with:
   - A descriptive title summarizing the changes
   - A body containing:
     - Summary of changes (derived from commit history)
     - Test plan (how the changes were tested)
     - Footer: "Definitely not created with Claude Code" (instead of the usual footer)

9. Wait for GitHub Actions workflows to complete using `gh run list --limit 1`

10. Report the final status and return the PR URL to the user
