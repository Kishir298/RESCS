# RESCS Security

## Reporting

Report vulnerabilities privately to the repository owner. Do not publish
reproduction details or customer data in an issue.

## Implemented controls

- `X-API-Key` authentication; keys are SHA-256 hashed and compared in constant
  time. `rescs setup` generates a random key and writes it `0600`.
- Owner isolation on every record, file, chunk and finalize operation,
  including bulk operations (403 on foreign ids).
- Path traversal protection: stored names are normalized and metacharacters
  are escaped when probing chunks.
- Upload quotas, per-file size caps, metadata caps and post-write rollback.
- Resumable uploads use exact chunk sizes, expiry and checksum verification,
  plus single-winner compare-and-set finalization.
- Bounded rate-limiter keys (10k LRU) to prevent unbounded memory growth.
- Signed CORE owner scope for Pi deployments (`X-RESCS-Signature`), with mount
  guards in front of storage paths.
- Browse of unknown ids never mutates storage; deletes are owner-checked.
- Release artifacts carry SHA-256 checksums and an SBOM.

## Operating guidance

- Keep the config file and storage directory owner-only.
- Bind to loopback unless a TLS reverse proxy terminates connections.
- Set `RESCS_API_KEY` from the environment in production; do not commit it.
- Back up the SQLite database and blob storage together; the backup tool's
  `--verify` re-hashes content.

## Known limitations

- RESCS does not terminate TLS itself; deploy behind a reverse proxy.
- S3 credentials are read from the environment and are not encrypted at rest
  by RESCS.
- Standalone binaries are unsigned unless signing is configured.
