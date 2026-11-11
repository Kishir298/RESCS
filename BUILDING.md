# Building RESCS

## Prerequisites

- Python 3.11+
- `python -m pip install build pyinstaller`

## Wheel and sdist

```bash
python -m build --wheel --sdist
```

## Standalone executable

```bash
python -m pip install -e . pyinstaller
python -m PyInstaller --onefile --name rescs \
  --collect-submodules rescs --collect-data rescs \
  --distpath dist scripts/standalone_entry.py
```

The frozen binary starts the server using the same CLI and configuration as
the installed command. Build per OS/architecture; no cross-compilation.

## Tests and lint

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m pytest -q
ruff check --select F src tests
```

Optional S3 tests need the `[s3]` extra and dummy credentials; live S3 is
never required for the default suite.

## Release automation

`.github/workflows/release.yml` builds wheels and binaries for Windows
x64/ARM64, macOS Intel/ARM64 and Linux x64/ARM64, then publishes checksums and
a CycloneDX SBOM. Debian/RPM packaging is not currently generated.

## Clean-install validation

```bash
python -m venv /tmp/rescs-clean
/tmp/rescs-clean/bin/pip install dist/rescs-*.whl
/tmp/rescs-clean/bin/rescs doctor
```
