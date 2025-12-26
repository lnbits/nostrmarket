# Stop LNbits Dev Server

Follow these steps:

1. Check if a server is running on port 5000 using `curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/`

2. If no server is running, inform the user that no dev server appears to be running on port 5000

3. If a server is running:
   - Find the process ID with `lsof -ti:5000`
   - Stop it with `kill $(lsof -ti:5000)`
   - Verify the server has stopped by checking the port again
   - Confirm to the user the server has been stopped

4. If the normal kill doesn't work, try `kill -9 $(lsof -ti:5000)` for a force kill
