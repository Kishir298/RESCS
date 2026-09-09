"""Resumable upload service: chunked sessions with integrity + expiry."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterable
from datetime import timedelta

from rescs.config import Settings
from rescs.domain import FileObjectData, UploadSessionData, normalize_tags, utcnow, validate_tags
from rescs.errors import ConflictError, InvalidRequestError, NotFoundError, PayloadTooLargeError, RESCSError, StorageError
from rescs.etag import file_etag
from rescs.interfaces.object_store import ObjectStore
from rescs.interfaces.repository import FileObjectRepository, UploadSessionRepository
from rescs.schemas.file_object import FileObjectCreate
from rescs.services.audit import AuditService
from rescs.services.expiry import resolve_expiry

MIN_CHUNK = 64 * 1024  # 64 KiB
MAX_CHUNK = 64 * 1024 * 1024  # 64 MiB
DEFAULT_CHUNK = 8 * 1024 * 1024  # 8 MiB
MAX_SESSION_SECONDS = 24 * 3600  # 24h


def _chunk_key(session_id: str, offset: int) -> str:
    return f"{session_id}__chunk__{offset:020d}"


class UploadService:
    def __init__(
        self,
        sessions: UploadSessionRepository,
        files_repo: FileObjectRepository,
        object_store: ObjectStore,
        *,
        settings: Settings | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self._sessions = sessions
        self._files = files_repo
        self._store = object_store
        self._settings = settings
        self._audit = audit

    def _audited(self, op: str, sid: str | None, owner: str, err: Exception | None = None) -> None:
        if self._audit is None:
            return
        if err is None:
            self._audit.log(op, resource_type="upload", resource_id=sid, owner=owner)
        else:
            code = err.code if isinstance(err, RESCSError) else type(err).__name__
            self._audit.log(op, resource_type="upload", resource_id=sid, owner=owner,
                            outcome="denied" if code in ("UNAUTHORIZED", "FORBIDDEN") else "error",
                            error_code=code)

    def create(
        self,
        *,
        owner: str,
        filename: str,
        content_type: str = "application/octet-stream",
        total_size: int,
        chunk_size: int = DEFAULT_CHUNK,
        checksum: str | None = None,
        metadata: dict | None = None,
        tags: list[str] | None = None,
        actor: str = "system",
    ) -> UploadSessionData:
        try:
            if total_size < 0:
                raise InvalidRequestError("total_size must be >= 0", details={"total_size": total_size})
            if not (MIN_CHUNK <= chunk_size <= MAX_CHUNK):
                raise InvalidRequestError(
                    f"chunk_size must be {MIN_CHUNK}..{MAX_CHUNK}",
                    details={"chunk_size": chunk_size},
                )
            max_file = self._settings.max_file_size if self._settings else 0
            if max_file and total_size > max_file:
                raise PayloadTooLargeError(f"total_size exceeds maximum {max_file}", details={"size": total_size, "max": max_file})
            norm_tags = normalize_tags(tags or [])
            validate_tags(norm_tags)
            now = utcnow()
            session = UploadSessionData(
                id=str(uuid.uuid4()),
                owner=owner,
                filename=filename or "unnamed",
                content_type=content_type or "application/octet-stream",
                total_size=total_size,
                received_bytes=0,
                chunk_size=chunk_size,
                status="active",
                checksum=checksum,
                created_at=now,
                updated_at=now,
                expires_at=now + timedelta(seconds=MAX_SESSION_SECONDS),
                metadata=metadata or {},
                tags=norm_tags,
            )
            created = self._sessions.create(session)
            self._audited("upload.create", created.id, owner)
            return created
        except Exception as exc:
            self._audited("upload.create", None, owner, exc)
            raise

    def get(self, session_id: str) -> UploadSessionData:
        session = self._sessions.get(session_id)
        if session.status != "active" or session.is_expired():
            if session.status == "active" and session.is_expired():
                session.status = "expired"
                try:
                    self._sessions.update(session)
                except NotFoundError:
                    pass
            raise NotFoundError("upload session expired or closed", details={"id": session_id})
        return session

    def put_chunk(self, session_id: str, offset: int, data: bytes, *, actor: str = "system") -> UploadSessionData:
        try:
            session = self.get(session_id)
            if offset < 0 or offset + len(data) > session.total_size:
                raise InvalidRequestError("chunk outside declared size", details={"offset": offset, "size": len(data), "total": session.total_size})
            if len(data) > session.chunk_size and not (offset == 0 and session.total_size <= session.chunk_size):
                # Allow final smaller chunk; intermediate chunks should respect chunk_size
                # but be lenient: only reject wildly oversized single chunks.
                if len(data) > MAX_CHUNK:
                    raise InvalidRequestError("chunk too large", details={"size": len(data)})
            key = _chunk_key(session_id, offset)
            # Duplicate chunk protection: identical offset+bytes is idempotent.
            if self._store.exists(key):
                existing = self._store.get(key)
                if existing == data:
                    return session
                # Conflicting overlapping chunk.
                raise ConflictError("conflicting chunk at offset", details={"offset": offset})
            # Overlap with different offsets is prevented by exact-offset keys;
            # partial overlaps would create gaps detected at finalize.
            self._store.put(key, data)
            # Recompute received bytes by scanning expected offsets (bounded: total/chunk).
            received = self._received(session)
            session.received_bytes = received
            session.updated_at = utcnow()
            updated = self._sessions.update(session)
            self._audited("upload.chunk", session_id, session.owner)
            return updated
        except Exception as exc:
            owner = actor
            try:
                owner = self._sessions.get(session_id).owner
            except Exception:
                pass
            self._audited("upload.chunk", session_id, owner, exc)
            raise

    def _received(self, session: UploadSessionData) -> int:
        # Sum contiguous bytes from offset 0 using stored chunk keys.
        # Chunks are fixed except possibly the last; walk offsets.
        received = 0
        offset = 0
        while offset < session.total_size:
            key = _chunk_key(session.id, offset)
            if not self._store.exists(key):
                break
            size = self._store.size(key)
            received += size
            if size == 0:
                break
            offset += size
            if offset > session.total_size:
                break
        return min(received, session.total_size)

    def finalize(self, session_id: str, *, actor: str = "system") -> FileObjectData:
        from rescs.services.files import FileService  # local import to avoid cycle

        try:
            session = self._sessions.get(session_id)
            if session.status != "active":
                raise InvalidRequestError("upload session is not active", details={"id": session_id, "status": session.status})
            if session.is_expired():
                session.status = "expired"
                self._sessions.update(session)
                raise NotFoundError("upload session expired", details={"id": session_id})
            # Verify all bytes present contiguously.
            chunks: list[bytes] = []
            offset = 0
            digest = hashlib.sha256()
            total = 0
            while offset < session.total_size:
                key = _chunk_key(session.id, offset)
                if not self._store.exists(key):
                    raise InvalidRequestError("missing chunk; upload incomplete", details={"offset": offset})
                data = self._store.get(key)
                if offset + len(data) > session.total_size:
                    raise InvalidRequestError("chunk exceeds declared size", details={"offset": offset})
                digest.update(data)
                chunks.append(data)
                total += len(data)
                offset += len(data)
            if total != session.total_size:
                raise InvalidRequestError("incomplete upload", details={"received": total, "total": session.total_size})
            hex_digest = digest.hexdigest()
            if session.checksum and session.checksum.lower() != hex_digest.lower():
                raise InvalidRequestError("checksum mismatch", details={"expected": session.checksum, "actual": hex_digest})
            # Publish via FileService.create (streams from memory-bounded list; chunks already bounded).
            payload = FileObjectCreate(
                filename=session.filename,
                mime_type=session.content_type,
                metadata=dict(session.metadata),
                owner=session.owner,
                tags=list(session.tags),
            )
            # Reuse file service logic without importing cycle at module load:
            # build a minimal FileObjectData directly with quota checks delegated to caller service?
            # Here we write blob + metadata atomically.
            file_id = str(uuid.uuid4())
            blob = b"".join(chunks)
            self._store.put(file_id, blob)
            now = utcnow()
            file_obj = FileObjectData(
                id=file_id,
                filename=session.filename,
                mime_type=session.content_type,
                size=total,
                storage_path=file_id,
                sha256=hex_digest,
                metadata=dict(session.metadata),
                owner=session.owner,
                version=1,
                etag=file_etag(hex_digest, total),
                created_at=now,
                updated_at=now,
                tags=list(session.tags),
            )
            try:
                created = self._files.create(file_obj)
            except Exception:
                self._store.delete(file_id)
                raise
            # Idempotent finalization: mark session finalized, cleanup chunks.
            session.status = "finalized"
            session.received_bytes = total
            session.updated_at = utcnow()
            try:
                self._sessions.update(session)
            except NotFoundError:
                pass
            self._cleanup_chunks(session.id, session.total_size)
            # Best-effort delete session record (keep audit via audit log).
            try:
                self._sessions.delete(session.id)
            except NotFoundError:
                pass
            self._audited("upload.finalize", session_id, session.owner)
            return created
        except Exception as exc:
            owner = actor
            try:
                owner = self._sessions.get(session_id).owner
            except Exception:
                pass
            self._audited("upload.finalize", session_id, owner, exc)
            raise

    def cancel(self, session_id: str, *, actor: str = "system") -> None:
        try:
            session = self._sessions.get(session_id)
            self._cleanup_chunks(session.id, session.total_size)
            try:
                self._sessions.delete(session.id)
            except NotFoundError:
                pass
            self._audited("upload.cancel", session_id, session.owner)
        except Exception as exc:
            self._audited("upload.cancel", session_id, actor, exc)
            raise

    def _cleanup_chunks(self, session_id: str, total_size: int) -> None:
        # Remove all chunk keys that may exist (bounded iterations).
        offset = 0
        # Walk by probing: try offsets in steps; also attempt direct prefix scan for local store.
        # Simple approach: iterate offsets 0..total in chunk increments is unknown; instead
        # try to delete keys by scanning: we stored exact offsets, so probe sequentially.
        # To avoid infinite loop on sparse offsets, cap iterations.
        seen_empty = 0
        while offset <= total_size and seen_empty < 3:
            key = _chunk_key(session_id, offset)
            if self._store.exists(key):
                try:
                    size = self._store.size(key)
                except Exception:
                    size = 0
                self._store.delete(key)
                offset += max(size, 1)
                seen_empty = 0
            else:
                # Advance by 1 to catch unaligned offsets? Use chunk scan fallback:
                # list local dir prefix if available.
                advanced = self._advance_probe(session_id, offset)
                if advanced is None:
                    break
                offset = advanced
                seen_empty += 1

    def _advance_probe(self, session_id: str, offset: int) -> int | None:
        # Generic fallback: try next plausible offsets by scanning store if it exposes listing.
        store = self._store
        prefix = f"{session_id}__chunk__"
        try:
            base = getattr(store, "_base", None)
            if base is not None:
                from pathlib import Path
                found: list[int] = []
                for p in Path(base).glob(prefix + "*"):
                    try:
                        off = int(p.name.split("__chunk__")[1])
                        if off > offset:
                            found.append(off)
                    except (ValueError, IndexError):
                        continue
                return min(found) if found else None
            blobs = getattr(store, "_blobs", None)
            if isinstance(blobs, dict):
                found = []
                for k in blobs.keys():
                    if k.startswith(prefix):
                        try:
                            off = int(k.split("__chunk__")[1])
                            if off > offset:
                                found.append(off)
                        except (ValueError, IndexError):
                            continue
                return min(found) if found else None
        except Exception:
            return None
        return None

    def cleanup_expired(self, *, actor: str = "system", limit: int = 500) -> int:
        expired = self._sessions.list_expired(utcnow(), limit=limit)
        count = 0
        for session in expired:
            try:
                self._cleanup_chunks(session.id, session.total_size)
                self._sessions.delete(session.id)
                count += 1
            except NotFoundError:
                continue
        if self._audit is not None:
            self._audit.log("upload.cleanup", resource_type="upload", owner=actor)
        return count
