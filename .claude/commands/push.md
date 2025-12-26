# Push Changes

Follow these steps:

1. Run `make check` and ensure all checks pass
   - Note: Requires `npm install` to have been run first for prettier

2. **Run Archie the Architect** - Invoke `/vet` to have Archie review the changes:
   - Archie will check for code quality issues
   - Archie will verify security concerns
   - Archie will check accessibility
   - Archie will review documentation
   - **If Archie finds Critical issues, DO NOT PUSH until resolved**

3. Check if the dev server is running on port 5000 using `curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/`

4. If the server is running:
   - Use the Claude Code Chrome extension to open http://localhost:5000 in a Chromium-based browser (Edge, Chrome, or Brave)
   - Visually verify the changes work correctly
   - Take a screenshot if needed to confirm

5. If the server is NOT running:
   - Ask the user to confirm they have tested their changes in the browser

6. Check if there are uncommitted changes with `git status`
   - If there are uncommitted changes, run `/commit` first

7. Check if there are commits to push with `git log origin/$(git branch --show-current)..HEAD --oneline`
   - If no commits to push, inform the user

8. Push the changes with `git push`

9. If the push fails due to no upstream branch, run `git push -u origin $(git branch --show-current)`

10. Monitor GitHub Actions for the push:
    - Run `gh run list --limit 1` to get the latest workflow run
    - Report the status to the user
