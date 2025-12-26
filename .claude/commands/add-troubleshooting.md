# Add Troubleshooting Entry

This command adds a new troubleshooting entry to the documentation.

**Arguments:** `$ARGUMENTS` - A description of the problem encountered

## Steps

1. Check if `docs/TROUBLESHOOTING.adoc` exists

2. If the file does NOT exist, create it with this initial structure:
   ```asciidoc
   = Troubleshooting Guide
   :toc:
   :toc-placement!:

   This document contains common problems and their solutions when working with the Nostr Market extension.

   toc::[]

   == Common Issues

   [cols="1,2", options="header"]
   |===
   | Problem | Solution

   |===
   ```

3. Analyze the problem described in `$ARGUMENTS`:
   - Understand what the user encountered
   - Determine the root cause
   - Formulate a clear, actionable solution

4. Add a new row to the table in `docs/TROUBLESHOOTING.adoc`:
   - Insert the new row BEFORE the closing `|===`
   - Format: `| <Problem description> | <Solution>`
   - Keep the problem description concise
   - Make the solution actionable and specific

5. Confirm the entry was added and show the user the new row

## Example

If called with: `/add-troubleshooting The make format command didn't run as missing dependencies`

Add a row like:
```
| `make format` fails with missing dependencies
| Run `npm install` to install Node.js dependencies (prettier), then run `make format` again.
```
