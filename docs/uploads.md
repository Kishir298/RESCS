# Resumable Uploads

`POST /api/v1/files` streams single-shot uploads (bounded memory via spool +
`put_stream`). For large/interrupted transfers use sessions:

## Flow

1. `POST /api/v1/uploads {filename, content_type, total_size, chunk_size, checksum?, metadata?, tags?}` → `201 {id, received_bytes:0, expires_at (+24h)}`
   - `chunk_size` 64KiB–64MiB, default 8MiB. `total_size` must respect `RESCS_MAX_FILE_SIZE`.
2. `PUT /api/v1/uploads/{id}/chunks?offset=N` (raw bytes, or `Content-Range: bytes N-M/T`) → `200 {received_bytes}`
   - Duplicate identical chunk is idempotent; conflicting bytes at same offset → `409`.
   - Chunks outside `[0,total)` → `400`.
3. `GET /api/v1/uploads/{id}` → status.
4. `POST /api/v1/uploads/{id}/finalize` → `200 FileObject` (SHA-256 verified, checksum mismatch → `400`, gaps → `400`). Atomic publish; no partial file visible.
5. `DELETE /api/v1/uploads/{id}` → cancel (`204`), chunks cleaned.

## Rules

- Owner-isolated; expired sessions read as `404` and are reclaimed by `POST /api/v1/admin/cleanup` (`uploads_cleaned`).
- Quotas enforced at finalize; failed finalization leaves no file.
- Concurrent finalize is safe: first wins, second sees closed session.
