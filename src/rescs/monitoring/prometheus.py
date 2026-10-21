"""Prometheus metrics exporter for RESCS."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# HTTP request metrics
rescs_http_requests_total = Counter(
    "rescs_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
rescs_http_request_duration_seconds = Histogram(
    "rescs_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

# Record operations
rescs_records_created_total = Counter(
    "rescs_records_created_total",
    "Total records created",
    ["namespace", "status"],
)
rescs_records_read_total = Counter(
    "rescs_records_read_total",
    "Total records read",
    ["namespace", "status"],
)
rescs_records_updated_total = Counter(
    "rescs_records_updated_total",
    "Total records updated",
    ["namespace", "status"],
)
rescs_records_deleted_total = Counter(
    "rescs_records_deleted_total",
    "Total records deleted",
    ["namespace", "status"],
)

# File operations
rescs_files_uploaded_total = Counter(
    "rescs_files_uploaded_total",
    "Total files uploaded",
    ["status"],
)
rescs_files_downloaded_total = Counter(
    "rescs_files_downloaded_total",
    "Total files downloaded",
    ["status"],
)
rescs_file_bytes_total = Counter(
    "rescs_file_bytes_total",
    "Total file bytes transferred",
    ["direction"],  # upload, download
)

# Upload sessions
rescs_upload_sessions_created_total = Counter(
    "rescs_upload_sessions_created_total",
    "Total upload sessions created",
)
rescs_upload_chunks_total = Counter(
    "rescs_upload_chunks_total",
    "Total upload chunks received",
    ["status"],
)
rescs_upload_finalized_total = Counter(
    "rescs_upload_finalized_total",
    "Total uploads finalized",
    ["status"],
)

# Bulk operations
rescs_bulk_operations_total = Counter(
    "rescs_bulk_operations_total",
    "Total bulk operations",
    ["operation", "status"],
)

# Quota metrics
rescs_quota_exceeded_total = Counter(
    "rescs_quota_exceeded_total",
    "Total quota exceeded events",
    ["quota_type"],  # records, files, bytes
)

# Storage metrics
rescs_storage_used_bytes = Gauge(
    "rescs_storage_used_bytes",
    "Storage used in bytes",
)
rescs_storage_available_bytes = Gauge(
    "rescs_storage_available_bytes",
    "Storage available in bytes",
)

# Database metrics
rescs_db_queries_total = Counter(
    "rescs_db_queries_total",
    "Total database queries",
    ["operation", "status"],
)
rescs_db_query_duration_seconds = Histogram(
    "rescs_db_query_duration_seconds",
    "Database query latency",
    ["operation"],
)

# S3 metrics
rescs_s3_operations_total = Counter(
    "rescs_s3_operations_total",
    "Total S3 operations",
    ["operation", "status"],
)
rescs_s3_bytes_total = Counter(
    "rescs_s3_bytes_total",
    "Total S3 bytes transferred",
    ["direction"],  # upload, download
)


def metrics_endpoint() -> Response:
    """FastAPI endpoint for Prometheus metrics."""
    from fastapi import Response as FastAPIResponse
    return FastAPIResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )