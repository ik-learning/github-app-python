# Debugging Guide

This guide helps you debug issues with your GitHub App.

---

## Viewing Logs

### View All Logs
```bash
docker-compose logs -f
```

### View Specific Service Logs
```bash
# App logs
make docker-logs-app
# or
docker-compose logs -f web-app

# Smee proxy logs
make docker-logs-smee
# or
docker-compose logs -f smee
```

### View Last N Lines
```bash
docker-compose logs --tail=100 web-app
```

---

## Understanding Log Levels

The app now has enhanced logging:

**Log Levels:**
- `DEBUG` - Detailed information, including headers and request details
- `INFO` - General informational messages
- `WARNING` - Warning messages (e.g., force pushes)
- `ERROR` - Error messages with stack traces

**What Gets Logged:**
```
2025-12-24 16:00:00 - __main__ - INFO - Incoming request: POST /webhooks/github
2025-12-24 16:00:00 - __main__ - DEBUG - Headers: {'x-github-event': 'push', ...}
2025-12-24 16:00:00 - __main__ - INFO - [STUB] Push: 2 commit(s) to main in owner/repo
2025-12-24 16:00:00 - __main__ - INFO - Response status: 200
```

---

## Common Errors

### 500 Internal Server Error

**Symptoms:**
```
web-app-1  | INFO: 172.20.0.3:43748 - "POST /webhooks/github HTTP/1.1" 500 Internal Server Error
smee-1     | POST http://web-app:8000/webhooks/github - 500
```

**Causes:**
1. **Handler Exception** - Error in event handler code
2. **Missing Environment Variable** - App ID, key, or secret not set
3. **Invalid Signature** - Webhook secret mismatch
4. **JSON Parsing Error** - Malformed webhook payload

**How to Debug:**

1. **Check detailed error logs:**
   ```bash
   make docker-logs-app
   ```

2. **Look for exception traces:**
   ```
   ERROR - Error processing request: ...
   Traceback (most recent call last):
   ...
   ```

3. **Common fixes:**
   - Verify environment variables are set
   - Check webhook secret matches GitHub App settings
   - Ensure handler code doesn't raise exceptions

### Handler Not Triggering

**Symptoms:**
```
# Webhook received but no [STUB] logs
INFO: "POST /webhooks/github HTTP/1.1" 200 OK
```

**Causes:**
1. Event type not registered (no `@github_app.on('event')` decorator)
2. Action doesn't match (e.g., `pull_request.synchronize` vs `pull_request.opened`)
3. Event filtered out by library

**How to Debug:**

1. **Check event type in logs:**
   ```
   DEBUG - Headers: {'x-github-event': 'pull_request', ...}
   ```

2. **Verify handler is registered:**
   ```python
   @github_app.on('pull_request.opened')  # Must match event + action
   async def handler(payload):
       ...
   ```

3. **Add catch-all handler for debugging:**
   ```python
   @github_app.on('*')  # Catches all events
   async def debug_handler(payload):
       logger.info(f"Received event: {payload.get('action')}")
       return {"status": "debug"}
   ```

### Signature Verification Failed

**Symptoms:**
```
ERROR - Invalid signature
403 Forbidden
```

**Causes:**
- `GITHUB_WEBHOOK_SECRET` doesn't match GitHub App settings
- Secret not base64 encoded when it should be (or vice versa)

**How to Fix:**
1. Go to GitHub App settings
2. Copy the webhook secret exactly
3. Set in environment: `export GITHUB_WEBHOOK_SECRET=your-secret`
4. Restart: `make docker-restart-app`

### Connection Refused

**Symptoms:**
```
smee-1 | Error: connect ECONNREFUSED 172.20.0.2:8000
```

**Causes:**
- App container not running
- Wrong target URL in smee configuration
- Network issues

**How to Fix:**
1. **Check app is running:**
   ```bash
   docker-compose ps
   ```

2. **Verify SMEE_TARGET:**
   ```bash
   # Should be: http://web-app:8000/webhooks/github
   echo $SMEE_TARGET
   ```

3. **Check network:**
   ```bash
   docker-compose exec smee ping web-app
   ```

---

## Debugging Workflow

### Step 1: Check Service Status
```bash
docker-compose ps
```

Expected output:
```
NAME        SERVICE   STATUS   PORTS
web-app-1   web-app   Up       0.0.0.0:8080->8000/tcp
smee-1      smee      Up
```

### Step 2: View Logs
```bash
# Terminal 1: Watch app logs
make docker-logs-app

# Terminal 2: Watch smee logs
make docker-logs-smee
```

### Step 3: Test Webhook
Trigger a webhook from GitHub (e.g., create a PR) and watch logs in real-time.

### Step 4: Check Response
Look for:
- ✅ `200 OK` - Success
- ❌ `500 Internal Server Error` - Check error logs
- ❌ `403 Forbidden` - Signature issue

### Step 5: Debug Handler
If webhook reaches the app but handler fails:

1. **Add debug logging to handler:**
   ```python
   @github_app.on('pull_request.opened')
   async def handler(payload):
       logger.debug(f"Full payload: {payload}")
       # Your code here
   ```

2. **Test with minimal handler:**
   ```python
   @github_app.on('pull_request.opened')
   async def handler(payload):
       logger.info("Handler called!")
       return {"status": "ok"}
   ```

3. **Gradually add back functionality** to find the issue

---

## Useful Debug Commands

### Inspect Container
```bash
# Enter app container
docker-compose exec web-app sh

# Check environment variables
docker-compose exec web-app env | grep GITHUB

# Check Python packages
docker-compose exec web-app pip list
```

### Test Webhook Endpoint Manually
```bash
# From host machine
curl -X POST http://localhost:8080/webhooks/github \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### Check Network
```bash
# List networks
docker network ls

# Inspect network
docker network inspect github-app-python_github-app-network
```

### Restart Services
```bash
# Restart app only
make docker-restart-app

# Restart everything
docker-compose restart

# Full rebuild
docker-compose down
docker-compose up --build
```

---

## Enable Extra Debug Info

### Enable Uvicorn Debug Mode

Edit `Dockerfile`:
```dockerfile
CMD ["pipenv", "run", "uvicorn", "src.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--log-level", "debug", \
     "--reload"]
```

### Enable FastAPI Debug Responses

Edit `src/app.py`:
```python
app = FastAPI(debug=True)  # Shows detailed error pages
```

### Add Request/Response Logging

Already added! The middleware logs:
- Incoming requests with method and path
- Request headers (at DEBUG level)
- Response status codes
- Full exception traces on errors

---

## Smee-Specific Debugging

### Smee Connection Issues

**Check Smee URL is valid:**
```bash
echo $SMEE_URL
# Should be: https://smee.io/YOUR_CHANNEL_ID
```

**Test Smee endpoint:**
```bash
curl $SMEE_URL
# Should return channel info
```

**Verbose Smee logs:**

Already enabled! Smee now runs with `--verbose` flag.

You'll see:
```
smee-1  | Connected to Smee.io
smee-1  | Forwarding events to http://web-app:8000/webhooks/github
smee-1  | Received event: push
smee-1  | POST http://web-app:8000/webhooks/github - 200
```

---

## GitHub App Configuration Checklist

Ensure your GitHub App is configured correctly:

- [ ] Webhook URL set to Smee channel URL
- [ ] Webhook secret matches `GITHUB_WEBHOOK_SECRET`
- [ ] App has required permissions:
  - Pull requests: Read & Write
  - Issues: Read & Write
  - Contents: Read-only (for push events)
- [ ] App is installed on target repository
- [ ] Events are subscribed:
  - [x] Pull request
  - [x] Issue comment
  - [x] Pull request review comment
  - [x] Push

---

## Performance Debugging

### Check Response Times
```bash
# App logs show processing time
grep "Response status" logs.txt
```

### Monitor Resource Usage
```bash
# Check container stats
docker stats

# Check app memory/CPU
docker stats web-app-1
```

### Profile Handlers

Add timing to handlers:
```python
import time

@github_app.on('pull_request.opened')
async def handler(payload):
    start = time.time()

    # Your code here

    duration = time.time() - start
    logger.info(f"Handler took {duration:.2f}s")
```

---

## Getting Help

If you're still stuck:

1. **Check logs with full context:**
   ```bash
   docker-compose logs --tail=200 > debug.log
   ```

2. **Capture webhook payload:**
   ```python
   @github_app.on('*')
   async def debug(payload):
       with open('/tmp/payload.json', 'w') as f:
           json.dump(payload, f, indent=2)
   ```

3. **Enable all debug logs:**
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

4. **Test handlers in isolation:**
   ```bash
   # Run tests
   make test-verbose
   ```

Remember: Most webhook issues are due to:
- Incorrect webhook secret
- Missing environment variables
- Event type/action mismatch
- Handler exceptions

Check these first! 🔍
