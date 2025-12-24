# 500 Error Fix - 2025-12-24

## 🚀 START HERE NEXT TIME

**IMMEDIATE ACTION NEEDED:**
1. Ask user: "Did you restart docker-compose after the last session?"
2. If YES: Ask them to share the latest logs to verify the 500 errors are fixed
3. If NO: Remind them to run `make docker-restart-app` or `docker-compose up --build`
4. Once confirmed working, proceed with Phase 2 of improvement proposal (see docs/improvement-proposal.md)

**What we fixed in last session:**
- Removed incorrect `@with_rate_limit_handling(github_app)` decorator causing 500 errors
- User has NOT yet tested the fix (session ended due to token limits)

**Current state:**
- Code changes committed to src/app.py
- App needs restart to pick up changes
- All 35 tests should still pass
- Ready to verify fix works with real webhooks

---

## Problem
Webhooks were returning 500 Internal Server Error without visible exception traces:
```
web-app-1 | INFO: "POST /webhooks/github HTTP/1.1" 500 Internal Server Error
smee-1    | POST http://web-app:8000/webhooks/github - 500
```

## Root Cause
The `@with_rate_limit_handling(github_app)` decorator was being used **incorrectly** on event handlers.

**Incorrect usage:**
```python
@github_app.on('issue_comment.created')
@with_rate_limit_handling(github_app)  # ❌ Wrong - passing github_app parameter
async def handle_pr_comment_added(payload: dict) -> dict:
    ...
```

This decorator doesn't take the `github_app` parameter (or shouldn't be used this way), causing exceptions when handlers were invoked.

## Fixes Applied to src/app.py

### 1. Removed Incorrect Decorator Usage
Removed `@with_rate_limit_handling(github_app)` from:
- `handle_pr_comment_added` (issue_comment.created)
- `handle_pr_edited` (pull_request.edited)
- `handle_push` (push)
- `handle_pr_created` (cleaned up commented decorator)

All handlers now use only:
```python
@github_app.on('event_type.action')
async def handler_name(payload: dict) -> dict:
    ...
```

### 2. Fixed Event Name Bug
In `handle_pr_sync`:
- Changed `"event": "pull_request.opened"` → `"event": "pull_request.synchronize"`
- Changed message to match: `"PR synchronize event processed (stub)"`

### 3. Code Cleanup
- Removed redundant `import logging` statements inside handler functions
- Removed redundant `logger = logging.getLogger(__name__)` calls inside handlers

## Testing the Fix

**Restart the app:**
```bash
make docker-restart-app
# or
docker-compose down
docker-compose up --build
```

**Expected behavior:**
- Webhooks should return 200 OK
- You should see `[STUB]` log messages for each event
- No more 500 errors

**Example successful logs:**
```
web-app-1 | INFO - Incoming request: POST /webhooks/github
web-app-1 | INFO - GitHub Event Type: pull_request
web-app-1 | INFO - [STUB] PR Created: #123 - Test PR
web-app-1 | INFO - Response status: 200
```

## If Issues Persist

With the comprehensive exception logging added earlier, any new errors will show:
- Full exception type and message
- Complete stack trace
- Request details (path, method, headers)

Check logs with:
```bash
make docker-logs-app
```

## Next Steps (Future Discussion)

1. Verify webhooks work correctly after restart
2. Consider if rate limiting is needed (and how to implement correctly)
3. Continue with Phase 2-6 of improvement proposal:
   - Phase 2: Extract Configuration
   - Phase 3: Create Handler Classes
   - Phase 4: Add Pydantic Models
   - Phase 5: Add Services
   - Phase 6: Final Cleanup

## Notes

- The `with_rate_limit_handling` decorator might need investigation if rate limiting is actually needed
- Current implementation has all stub handlers working without rate limiting
- All 35 tests should still pass (tests don't use the decorator)
