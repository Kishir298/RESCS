# RESCS Compatibility

Machine-readable source of truth: [`compatibility.json`](compatibility.json).

## Platforms

| OS | Architectures | Minimum | Status |
| --- | --- | --- | --- |
| Windows | x86_64, arm64 | 10 22H2 | CI smoke on windows-latest; Win10 needs hardware validation |
| macOS | x86_64, arm64 | 12.0 | CI smoke on macos-latest |
| Linux | x86_64, arm64 | glibc 2.28 | CI tests on ubuntu-latest |
| Raspberry Pi OS | arm64 | Bookworm | deployment scripts; validated on Pi hardware in project docs |

## Runtime

- Python 3.11+, console command `rescs`.
- Storage backends: `local` (default), `memory` (tests), `s3` (`.[s3]` extra).

## CORE integration

Optional. RESCS publishes `/api/v1/contract` and accepts CORE owner-scoped
requests signed with `X-RESCS-Signature`. When CORE is absent, local API-key
operation is unaffected. CORE protocol `0.3.0`/`0.4.0` are accepted by the
shared client.

## Validation levels

1. Source compilation and tests: verified.
2. Package generation: release workflow.
3. Installer: not tested on physical Windows hardware here.
4. Runtime: macOS local tests and CI smoke on Linux/Windows/macOS.
5. Physical hardware: Pi deployment documented separately; Windows 10/ARM64
   and macOS Intel are **not** verified.

## Not provided

- Debian/RPM native packages.
- Windows/macOS service installers (run `rescs setup` and start manually or
  with a user-level service manager).
