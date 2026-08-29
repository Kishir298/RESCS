# Changelog

All notable changes to R.E.S.C.S. are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/).
Versioning follows [Semantic Versioning](https://semver.org/).

## Unreleased

### Added - Phase 1 (foundation)

- `src/rescs` package with application factory (`create_app`)
- Environment / `.env` configuration via pydantic-settings (`RESCS_*`)
- Required API key configuration (`RESCS_API_KEY`, min 16 chars)
- Logging foundation (`rescs.logging`)
- Domain error hierarchy with stable codes and HTTP status mapping
- Health/readiness reporting foundation (`rescs.health`)
- Health endpoints: `/health/live`, `/health/ready`, `/health`
- Project metadata (`pyproject.toml`), pinned dependencies, `.gitignore`,
  `.env.example`
- Test suite: configuration, errors, health service, health API