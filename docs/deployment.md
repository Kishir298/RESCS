# Deployment

## Configure (env only)

Required: `RESCS_API_KEY` (≥16 chars). See `.env.example` for `RESCS_ENV`,
`RESCS_DATABASE_URL`, `RESCS_STORAGE_DIR`/`RESCS_STORAGE_BACKEND`, quotas,
`RESCS_MAX_TTL_SECONDS`, `RESCS_STREAMING_THRESHOLD_BYTES`, `RESCS_RATE_LIMIT_*`.

## Run

```bash
python -m uvicorn rescs.main:create_app --factory --host 0.0.0.0 --port 8000
```

- `RESCS_AUTO_CREATE_SCHEMA=true` for dev/test; `false` + migration-managed schema in prod.
- Liveness `GET /health/live` (process), readiness `GET /health/ready` (200 only when DB + storage probes pass, else 503).

## Checks

- HTTPS at ingress, request IDs (`X-Request-ID`) logged, no secrets in logs.
- PostgreSQL: `postgresql+psycopg://` URL, `pool_pre_ping`, gated compat test via `RESCS_INTEGRATION_DATABASE_URL` (test-only env, not app config).
- S3: `RESCS_STORAGE_BACKEND=s3` + endpoint/bucket/region/keys; local remains default. Live S3 needs `pip install boto3` (optional, not in base `requirements.txt`); without it the backend fails fast with `STORAGE_ERROR`.
- packaging: `requirements.txt` is the runtime source of truth (`pyproject.toml` has no `dependencies=[]` yet — do not `pip install -e .` expecting deps).
- Backups daily + 7-day retention (`docs/backups.md`); encryption per `docs/encryption.md`.

Production multi-instance, real S3/HTTPS, and 24/7 endurance are **external validation**.
