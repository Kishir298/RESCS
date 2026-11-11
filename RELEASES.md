# RESCS Releases

R.E.S.C.S. versions independently. Current: `0.4.0` (`pyproject.toml`,
`compatibility.json`).

## Channels

| Channel | Trigger | Result |
| --- | --- | --- |
| Stable | tag `vX.Y.Z` | GitHub Release |
| Beta | tag `vX.Y.Z-beta.N` | prerelease |
| Development | `workflow_dispatch` | artifacts only |

## Artifacts

`RESCS-<version>-<os>-<arch>-<format>`:

- `RESCS-<v>-windows-x64.zip` (`rescs.exe`), `-windows-arm64.zip` (experimental)
- `RESCS-<v>-macos-x86_64.tar.gz`, `-macos-arm64.tar.gz`
- `RESCS-<v>-linux-x64.tar.gz`, `-linux-arm64.tar.gz`
- `RESCS-<v>-python-wheel.whl`, `-python-sdist.tar.gz`
- `SHA256SUMS`, `sbom.cdx.json`

## Process

1. Bump the version in `pyproject.toml`, `compatibility.json` and
   `CHANGELOG.md`.
2. Run `pytest` and `ruff check --select F src tests`.
3. Commit; tag `vX.Y.Z`; push the tag.
4. The workflow validates version/manifest agreement, builds the matrix,
   verifies the artifacts, then publishes.
5. A failed required job prevents publishing.

## Known limitations

- Debian `.deb` / RPM packages are not produced; portable archives and wheels
  are the supported formats.
- Windows ARM64 is experimental.
- macOS binaries are unsigned unless signing secrets are configured.
- The Raspberry Pi installer is optional and Pi-specific; it is not part of the
  generic release matrix.
