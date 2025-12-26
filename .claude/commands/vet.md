# Vet Extension (Archie's Review)

This command invokes **Archie the Architect** to perform a comprehensive code review.

## Steps

1. **Launch Archie** - Use the Task tool to spawn Archie the Architect agent:
   ```
   Task tool with subagent_type: "general-purpose"
   Prompt: "You are Archie the Architect. Read .claude/agents/archie.md for your role and responsibilities. Perform a comprehensive review of the recent changes in this extension."
   ```

2. **Provide context to Archie**:
   - Run `git diff origin/main..HEAD` to show all changes
   - Run `git diff --name-only origin/main..HEAD` to list changed files
   - Include the current branch name

3. **Wait for Archie's review** - Archie will:
   - Review all changed files against his checklist
   - Check for security concerns
   - Verify Quasar component usage
   - Check accessibility
   - Review documentation in `/docs/*.adoc`
   - Provide a structured report

4. **Report results** - Present Archie's findings:
   - Critical issues (must fix before push)
   - Warnings (should fix)
   - Suggestions (nice to have)
   - Approval status

5. **Handle Critical Issues**:
   - If Critical issues found, list them clearly
   - Do NOT proceed with push until resolved
   - Offer to help fix the issues

## Optional Arguments

- `$ARGUMENTS` can specify a specific file or area to review:
  - `/vet views_api.py` - Review only the API file
  - `/vet templates/` - Review only templates
  - `/vet security` - Focus on security concerns
  - `/vet accessibility` - Focus on accessibility audit
