# R.E.S.C.S. File Storage

## Separation of metadata and bytes

Large binary payloads never live inside database rows. Each file is split
into:

- **Metadata** — `file_objects` database row: id, filename, MIME type, size,
  SHA-256, owner, version, etag, timestamps.
- **Blob** — the raw bytes in an object store, addressed by the file id.

```
FileService
    |                          [
    +-- metadata  ->  FileObjectRepository (PostgreSQL / SQLite host)
    |
    +-- blob      ->  ObjectStore  (local filesystem now,
                                    S3-compatible / Supabase Storage later)
```

## Object store abstraction

`rescs/interfaces/object_store.py` defines a `Protocol` with:

```
put(object_id, data) -> None
get(object_id) -> bytes          # raises StorageError when missing
delete(object_id) -> None
exists(object_id) -> bool
```

Implemented backends:

| Backend | Location | Use |
| --- | --- | --- |
| `LocalObjectStore` | `rescs/storage/local.py` | local filesystem under `RESCS_STORAGE_DIR` (default) |
| `MemoryObjectStore` | `rescs/storage/memory.py` | deterministic test double |

A cloud object store implements the same protocol; the storage service and
API are unchanged.

## File lifecycle

- **Create/upload** — bytes hashed (SHA-256), written to the object store,
  then metadata recorded. If the metadata write fails the blob is cleaned up.
- **Read/download** — metadata read from the repository, bytes read from the
  store. Metadata without a blob surfaces as `STORAGE_ERROR`.
- **Delete** — metadata removed first; blob cleanup is best-effort and
  logged.
- **List** — paginated metadata listing with owner filtering.

## Integrity

- Every upload gets a content-derived `sha256` and a deterministic `etag`
  (hash of fingerprint + size).
- File ids are UUIDs; the local store validates identifiers to prevent path
  traversal.
- Idempotent uploads via `idempotency_key`.