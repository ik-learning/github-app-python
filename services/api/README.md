# API Service

GitHub App webhook handler that fans out work to Redis streams and receives callbacks from workers.

## Endpoints

### `GET /status`
Health check. Returns app and Redis connection status.

### `POST /fanout`
Publishes messages to worker streams (`worker-1`).

- Generates an `id` (UUID7) for tracking
- Stores full payload in Redis with key `storage:{id}` containing: `id`, `name`, `owner`, `branch`, `prId`
- Sends worker message to each stream with: `id`, `callback_url`
- Returns the `id` and streams list

### `POST /callback`
Receives completion callbacks from workers.

- Expects: `{ "id": "...", "app_name": "...", "msg": "..." }`
- Reads storage data from Redis by `id`
- Logs `name`, `owner`, `branch` from storage along with `msg`

### `POST /webhooks/github`
GitHub App webhook endpoint. Handles:
- `pull_request.opened`
- `pull_request.synchronize`

## Message Flow

```
GitHub Event → API → Redis Streams → Workers → /callback
```
