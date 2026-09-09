"""Machine-readable integration contract exposed to C.O.R.E.

RESCS and C.O.R.E. are developed and released independently and never import
each other; this module is the *shared surface* they agree on at runtime.
C.O.R.E. can discover capabilities, conventions and guarantees by calling the
``/api/v1/contract`` endpoint rather than hard-coding them.
"""

from __future__ import annotations

from typing import Any

from rescs.api import API_VERSION
from rescs.config import Settings

RESERVED_NAMESPACE_PREFIXES = ("core.", "rescs.")

CAPABILITIES: dict[str, list[str]] = {
    "records": ["create", "put", "get", "update", "delete", "restore", "purge", "bulk", "list", "search"],
    "files": ["upload", "metadata", "download", "delete", "restore", "purge", "list"],
    "consistency": ["version", "etag", "if_match", "idempotency", "soft_delete", "ttl"],
    "organization": ["tags", "filters", "deleted_listing"],
    "governance": ["quotas", "bulk_bounds", "metadata_caps"],
    "security": ["x_api_key", "owner_scoping"],
    "health": ["live", "ready"],
    "operations": ["cleanup", "audit"],
}

CONTRACT_DOC = "docs/core-integration-contract.md"


def build_contract(settings: Settings) -> dict[str, Any]:
    """Describe RESCS capabilities and conventions truthfully."""
    return {
        "service": settings.app_name,
        "version": settings.version,
        "api_version": API_VERSION,
        "documentation": "/docs",
        "contract_documentation": CONTRACT_DOC,
        "transport": "http",
        "auth": {"method": "header", "header": "X-API-Key"},
        "owner": {
            "default": "system",
            "locked": bool(settings.api_key_owner),
            "locked_to": settings.api_key_owner or None,
        },
        "pagination": {
            "limit_min": 1,
            "limit_max": 500,
            "limit_default": 100,
        },
        "reserved_namespaces": list(RESERVED_NAMESPACE_PREFIXES),
        "error_envelope": {
            "shape": {
                "error": {"code": "str", "message": "str", "details": "object|null"}
            },
            "sample": {"code": "NOT_FOUND", "message": "record not found"},
            "codes": [
                "INVALID_REQUEST",
                "UNAUTHORIZED",
                "FORBIDDEN",
                "NOT_FOUND",
                "CONFLICT",
                "PRECONDITION_FAILED",
                "PAYLOAD_TOO_LARGE",
                "QUOTA_EXCEEDED",
                "VALIDATION_ERROR",
                "STORAGE_ERROR",
                "INTERNAL_ERROR",
                "DEPENDENCY_UNAVAILABLE",
            ],
        },
        "etag": {
            "canonical": "hex-sha256",
            "if_match_forms": ["bare", "quoted", "weak", "*"],
            "mutation_routes": [
                "PATCH /api/v1/records/{id}",
                "PUT /api/v1/records",
                "DELETE /api/v1/records/{id}",
                "POST /api/v1/records/{id}/restore",
                "DELETE /api/v1/records/{id}/purge",
                "DELETE /api/v1/files/{id}",
                "POST /api/v1/files/{id}/restore",
                "DELETE /api/v1/files/{id}/purge",
            ],
        },
        "blob_integrity": {
            "sha256": True,
            "verify_on_download": True,
        },
        "capabilities": CAPABILITIES,
        "endpoints": {
            "records": "/api/v1/records",
            "records_bulk": "/api/v1/records/bulk",
            "files": "/api/v1/files",
            "contract": f"/api/{API_VERSION}/contract",
            "health": ["/health/live", "/health/ready"],
            "admin_cleanup": f"/api/{API_VERSION}/admin/cleanup",
            "admin_audit": f"/api/{API_VERSION}/admin/audit",
            "admin_deleted_records": f"/api/{API_VERSION}/admin/records/deleted",
            "admin_deleted_files": f"/api/{API_VERSION}/admin/files/deleted",
        },
    }