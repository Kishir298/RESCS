# Backups & Disaster Recovery

Resource `restore` (undelete a tombstone) is NOT system backup.

## What is backed up

1. **Database metadata** (`records`, `file_objects`, `audit_events`, `upload_sessions`)
2. **Blobs** (object-store directory or S3 bucket)
3. **Config references** (never secrets)

## Tool

`python scripts/rescs_backup.py --database-url $RESCS_DATABASE_URL --storage-dir $RESCS_STORAGE_DIR --out backups/YYYYMMDD`

Produces `db.dump`, `blobs/`, `manifest.json` (SHA-256 per blob).

- SQLite: online `sqlite3.backup` copy.
- PostgreSQL: use `pg_dump -Fc` (script records hint; automate via cron).
- S3 backend: sync bucket prefix (`aws s3 sync`) alongside DB dump.

## Retention / RPO / RTO

- Baseline: **daily, 7-day retention**.
- RPO: ≤24h. RTO: <1h for small deployments (restore DB, restore blobs, verify manifest).

## Restore

1. Stop writers.
2. Restore DB (`sqlite3 restore.db ".restore db.dump"` or `pg_restore`).
3. Restore blobs to `RESCS_STORAGE_DIR` (or S3 prefix).
4. Verify: re-hash blobs vs `manifest.json`; run `GET /health/ready` (must be 200); spot-check `GET /api/v1/records` + file download SHA.
5. Resume traffic.

## Consistency

Backup DB and blobs as close together as possible. Orphan blobs (no metadata) are harmless; missing blobs surface as `500 STORAGE_ERROR` with expected/actual SHA and never as false success. `POST /api/v1/admin/cleanup` after restore reclaims expired leftovers.

Live S3 versioning + PITR + real restore drill remain **external validation**.
