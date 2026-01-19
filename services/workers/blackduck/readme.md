# Blackduck Worker

Worker service that subscribes to a Redis stream and processes incoming messages.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STREAM_NAME` | Redis stream to subscribe to | `worker-1` |
| `REDIS_HOST` | Redis server hostname | `localhost` |
| `REDIS_PORT` | Redis server port | `6379` |
| `PORT` | HTTP server port | `8000` |

## Endpoints

- `GET /status` - Health check, returns app and Redis connection status

## How It Works

1. On startup, a background thread subscribes to the configured Redis stream using `XREAD`
2. Messages are read with blocking (waits indefinitely for new messages)
3. Received messages are logged to stdout

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
REDIS_HOST=localhost STREAM_NAME=worker-1 python app.py
```

## Docker

```bash
docker build -f services/workers/blackduck/Dockerfile -t worker-blackduck .
docker run --rm -e REDIS_HOST=redis -e STREAM_NAME=worker-1 worker-blackduck
```
