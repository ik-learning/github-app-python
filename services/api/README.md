# App

Uses Redis Streams (XADD) so workers can consume with XREAD/XREADGROUP.

## What

- Connects to Redis (configurable via REDIS_HOST and REDIS_PORT env vars)
- Publishes to 3 streams: worker-1, worker-2, worker-3
- Sends static message: {name, owner, branch, prId}
