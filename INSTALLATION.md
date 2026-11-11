# RESCS Installation

R.E.S.C.S. runs as an independent storage service. It does not require a
Raspberry Pi, CORE or another RISARMS component. Python 3.11+.

## pip / pipx

```bash
python -m pip install .
pipx install .                 # global `rescs` command
```

Optional S3 backend: `python -m pip install ".[s3]"`.

## Commands

```bash
rescs --help
rescs setup                    # private config with a random API key (0600)
rescs doctor                   # config/storage/import checks; no network
rescs                          # serve on 127.0.0.1:8081
rescs --host 0.0.0.0 --allow-remote --port 8081
```

`rescs setup` creates the per-user configuration file once. Re-running it
preserves the existing file and secrets.

Data locations:

- Windows: `%LOCALAPPDATA%\RESCS`
- macOS: `~/Library/Application Support/RESCS`
- Linux: `$XDG_DATA_HOME/rescs` or `~/.local/share/rescs`

Override with `--config`.

## Windows

- Windows 10 22H2 and Windows 11, x64 (ARM64 where wheels exist).
- PowerShell 5.1 works. `rescs setup` prints a reminder to restrict the
  config file ACL to your account; do that before exposing the service.

## macOS

- Intel and Apple Silicon.
- Add `~/.local/bin` or the pipx bin directory to `~/.zshrc` for the global
  command.

## Linux (server)

```bash
rescs setup
RESCS_CONFIG=~/.local/share/rescs/rescs.env rescs --host 127.0.0.1
```

For systemd deployments, run `rescs` as a dedicated user, keep the storage
directory owner-only, and place a TLS reverse proxy in front of it when remote
access is needed. The bundled Pi installer (`deploy/pi`) is optional and
Pi-specific.

## CORE integration (optional)

RESCS exposes `/api/v1/contract` and authenticates with `X-API-Key`. CORE can
use it, but RESCS works without CORE. When CORE integration is enabled, the
device/owner authorization rules still apply to every record and file.

## Updating

Reinstall the package. The configuration, SQLite database and stored files
are preserved. No configuration is overwritten without an explicit new path.

## Uninstall

```bash
python -m pip uninstall rescs        # or: pipx uninstall rescs
```

Uninstalling does not delete the database or stored files. Remove the data
directory manually only when you intend to erase data.

## Standalone executables

Release builds provide `rescs.exe` and POSIX `rescs` binaries, plus wheels.
