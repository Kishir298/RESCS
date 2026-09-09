# Rate Limiting

Disabled by default. Enable with:

```text
RESCS_RATE_LIMIT_ENABLED=true
RESCS_RATE_LIMIT_GENERAL_PER_MINUTE=100
RESCS_RATE_LIMIT_WRITES_PER_MINUTE=60
RESCS_RATE_LIMIT_UPLOADS_PER_MINUTE=20
```

- Buckets by API key: `general` (GETs), `writes` (POST/PUT/PATCH/DELETE), `uploads` (`POST /files`, `/uploads*`).
- Exceeded → `429 {error:{code:RATE_LIMITED}}` + `Retry-After` seconds + `X-RateLimit-*` headers.
- `/health/*` and `/` never limited; tests run with limiter off.
- **Single-instance in-memory sliding window.** Multi-instance prod needs a shared
  backend (Redis) — document as external work, do not rely on this limiter alone.
