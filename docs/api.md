# R.E.S.C.S. HTTP API

Interactive documentation is generated automatically at `/docs` (Swagger UI)
and `/redoc`. Versioned under `/api/v1`.

## Convention

- Requests/responses are JSON unless noted (file uploads/downloads are
  binary multipart).
- List endpoints paginate with `limit` (1..500, default 100) and `offset`.
- Every error follows the envelope:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "record not found",
    "details": { "id": "..." }
  }
}
```

| HTTP | Code | Meaning |
| --- | --- | --- |
| 400 | `INVALID_REQUEST` | malformed request semantics |
| 401 | `UNAUTHORIZED` | missing/invalid credentials |
| 403 | `FORBIDDEN` | authenticated but not allowed |
| 404 | `NOT_FOUND` | unknown resource |
| 409 | `CONFLICT` | violates uniqueness |
| 422 | `VALIDATION_ERROR` | body fails validation |
| 500 | `STORAGE_ERROR` / `INTERNAL_ERROR` | storage/backend failure |
| 503 | `DEPENDENCY_UNAVAILABLE` | database/object store unreachable |

## Records

### Create

```
POST /api/v1/records        -> 201 Record
```

```json
{ "namespace": "default", "key": "profile", "value": { "name": "x" }, "metadata": {} }
```

Adding an `idempotency_key` makes the create idempotent (same key returns the
existing record).

### Upsert by namespace/key

```
PUT /api/v1/records         -> 200 Record
```

Creates or replaces the record for `(namespace, key)`; bumps `version`.

### Read

```
GET /api/v1/records/{id}    -> 200 Record
```

### Partial update

```
PATCH /api/v1/records/{id}  -> 200 Record
```

Body may contain any of `value`, `metadata`, `namespace`, `key`. Version is
incremented and the etag recomputed.

### Delete

```
DELETE /api/v1/records/{id} -> 204
```

### List / search

```
GET /api/v1/records?namespace=&key_prefix=&owner=&limit=&offset=
GET /api/v1/records?query=blue&namespace=&owner=&limit=&offset=
```

`query` performs a case-insensitive substring search across key, value and
metadata. `key_prefix` filters the key without searching content. Response:

```json
{ "items": [Record, ...], "total": 7, "limit": 100, "offset": 0 }
```

## Files

### Upload

```
POST /api/v1/files          -> 201 File (multipart/form-data)
```

Field: `upload` (the file bytes). Filename and Content-Type are taken from
the part. The server computes `size`, `sha256` and `etag`.

### Metadata

```
GET /api/v1/files/{id}      -> 200 File
```

### Download

```
GET /api/v1/files/{id}/content -> 200 bytes
```

Response headers: `Content-Type`, `Content-Disposition`, `ETag`,
`X-File-SHA256`, `X-File-Size`.

### Delete

```
DELETE /api/v1/files/{id}   -> 204
```

### List

```
GET /api/v1/files?owner=&limit=&offset=
```

## Health

```
GET /health/live    -> process liveness
GET /health/ready   -> dependency readiness (database, storage)
GET /health         -> full status
```

## Record / File document shapes

```
Record {
  id, namespace, key, value, metadata, owner,
  version, idempotency_key, etag, created_at, updated_at
}
File {
  id, filename, mime_type, size, storage_path, sha256, metadata, owner,
  version, idempotency_key, etag, created_at, updated_at
}
```