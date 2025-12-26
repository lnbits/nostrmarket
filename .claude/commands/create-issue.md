# Create GitHub Issue

This command creates a new issue in the nostrmarket repository.

**Arguments:** `$ARGUMENTS` - Description of the issue to create

## Steps

1. **Check for issue templates** - Look for templates in `.github/ISSUE_TEMPLATE/`:
   ```bash
   ls -la .github/ISSUE_TEMPLATE/ 2>/dev/null || echo "No templates found"
   ```
   If templates exist, use the appropriate template structure.

2. **Determine issue type** from the prompt:
   - `[FEAT]` - New feature request
   - `[BUG]` - Bug report
   - `[ENHANCEMENT]` - Improvement to existing feature

3. **Gather context**:
   - Current branch: `git branch --show-current`
   - Recent commits: `git log --oneline -3`
   - If it's a bug, ask for:
     - Steps to reproduce
     - Expected behavior
     - Actual behavior
     - Environment details (browser, OS, LNbits version)
     - Any error logs
     - Screenshots if available

4. **Create the issue** using `gh issue create`:
   ```bash
   gh issue create \
     --repo lnbits/nostrmarket \
     --title "[TYPE] Title here" \
     --body "$(cat <<'EOF'
   ## Description
   [Clear description of the issue]

   ## Steps to Reproduce (for bugs)
   1. Step one
   2. Step two
   3. Step three

   ## Expected Behavior
   [What should happen]

   ## Actual Behavior
   [What actually happens]

   ## Environment
   - **Browser**: [e.g., Chrome 120, Firefox 121, Edge]
   - **OS**: [e.g., Ubuntu 22.04, Windows 11, macOS 14]
   - **LNbits Version**: [e.g., 0.12.0]
   - **Extension Version**: [commit hash or version]

   ## Logs
   ```
   [Any relevant error logs]
   ```

   ## Screenshots
   [Attach screenshots if applicable]

   ---
   Definitely not created with Claude Code
   EOF
   )"
   ```

5. **Report the issue URL** to the user

## Examples

**Feature request:**
```
/create-issue Add dark mode support for the marketplace
```
Creates: `[FEAT] Add dark mode support for the marketplace`

**Bug report:**
```
/create-issue Orders not showing when filtering by customer
```
Creates: `[BUG] Orders not showing when filtering by customer`

**Enhancement:**
```
/create-issue Improve loading performance on products page
```
Creates: `[ENHANCEMENT] Improve loading performance on products page`

## Notes

- Always include environment details for bugs
- Reference related PRs or issues if known
- Add appropriate labels if you have permission
- The footer says "Definitely not created with Claude Code" (it's a joke, obviously it was)
