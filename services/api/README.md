# API Service

GitHub App webhook handler that fans out work to Redis streams and receives callbacks from workers.

## Endpoints

### `GET /status`
Health check. Returns app and Redis connection status.

### `POST /fanout`
Publishes messages to worker streams (`worker-1`, `worker-2`, `worker-3`).

- Generates a `trace_id` (UUID7) for tracking
- Sends message with: `trace_id`, `name`, `owner`, `branch`, `prId`, `callbackUrl`
- Returns the `trace_id` for correlation

### `POST /callback`
Receives completion callbacks from workers.

- Expects: `{ "trace_id": "...", "msg_base64": "..." }`
- Logs the callback for tracking

### `POST /webhooks/github`
GitHub App webhook endpoint. Handles:
- `pull_request.opened`
- `pull_request.synchronize`

## Message Flow

```
GitHub Event → API → Redis Streams → Workers → /callback
```
