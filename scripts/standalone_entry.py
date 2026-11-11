"""Frozen-executable entry point for R.E.S.C.S. (used only by PyInstaller)."""

from rescs.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
