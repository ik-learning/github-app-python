# Blackduck Worker

Worker service that subscribes to a Redis stream and processes incoming messages.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STREAM_NAME` | Redis stream to subscribe to | `worker-1` |
| `REDIS_HOST` | Redis server hostname | `localhost` |
| `REDIS_PORT` | Redis server port | `6379` |
| `PORT` | HTTP server port | `8000` |
| `APP_NAME` | Application name for logging | - |
| `CONSUMER_GROUP` | Redis consumer group name | `workers` |
| `CONSUMER_NAME` | This consumer's identifier | `APP_NAME` or `consumer-1` |

## Endpoints

- `GET /status` - Health check, returns app and Redis connection status

## How It Works

1. On startup, creates a consumer group if it doesn't exist (`XGROUP CREATE`)
2. A background thread subscribes to the stream using `XREADGROUP`
3. Messages are read with 5-second blocking timeout
4. After processing, messages are acknowledged (`XACK`) and deleted (`XDEL`)

### Consumer Groups

The worker uses Redis consumer groups which provide:
- **At-least-once delivery** - messages are tracked per consumer
- **Message acknowledgment** - only removed after successful processing
- **Multiple consumers** - scale by running multiple instances with different `CONSUMER_NAME`

### Message Lifecycle

```
Producer (XADD) → Stream → Consumer (XREADGROUP) → Process → XACK → XDEL
```

## Message Format

The worker expects messages pushed via `XADD` with a `data` field containing JSON:

```json
{
  "name": "repo",
  "owner": "octocat",
  "branch": "feature-branch",
  "prId": 42
}
```

## Running Locally

```bash
REDIS_HOST=localhost STREAM_NAME=worker-1 APP_NAME=blackduck python app.py
```

## Docker

```bash
docker build -f services/workers/blackduck/Dockerfile -t worker-blackduck .
docker run --rm -e REDIS_HOST=redis -e STREAM_NAME=worker-1 -e APP_NAME=blackduck worker-blackduck
```
