# Test Changes (Teddie's Review)

This command invokes **Teddie the Tester** to test recent changes.

## Steps

1. **Launch Teddie** - Use the Task tool to spawn Teddie the Tester agent:

   ```
   Task tool with subagent_type: "general-purpose"
   Prompt: "You are Teddie the Tester. Read .claude/agents/teddie.md for your role and responsibilities. Test the recent changes in this extension."
   ```

2. **Provide context to Teddie**:
   - Run `git diff --name-only origin/main..HEAD` to list changed files
   - Identify which areas need testing (API, UI, etc.)

3. **Teddie will**:
   - Check if dev server is running on port 5000
   - Use Claude Code Chrome extension to visually verify UI changes
   - Run existing tests with `make test`
   - Create new tests if needed in `/tests/`
   - Update `/docs/TESTING.adoc` if testing procedures changed

4. **Report results**:
   - Tests run and their results
   - Visual verification status
   - Any new tests created
   - Issues found during testing

## Optional Arguments

- `$ARGUMENTS` can specify what to test:
  - `/test api` - Test API endpoints only
  - `/test ui` - Test UI components only
  - `/test merchant` - Test merchant-related functionality
