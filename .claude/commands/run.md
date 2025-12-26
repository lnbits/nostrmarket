# Run LNbits Dev Server

Follow these steps:

1. Check if a server is already running on port 5000 using `curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/`

2. If port 5000 is already in use:
   - Check what's running with `lsof -ti:5000`
   - If it's already LNbits, inform the user it's already running
   - Otherwise, ask the user if they want to stop the existing process

3. Read the LNBITS_PATH from `.env.dev` file (or use default `../lnbits`)

4. Change to the LNbits directory and start the server as a **background process**:
   - Use the Bash tool with `run_in_background: true` parameter
   - Command: `cd $LNBITS_PATH && uv run lnbits`
   - This allows the user to continue working while the server runs

5. Wait a few seconds for the server to start

6. Verify the server is running by checking port 5000

7. Inform the user the server is available at `http://localhost:5000`
