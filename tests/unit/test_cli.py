"""Installed launcher: strict configuration failures must be actionable."""

from __future__ import annotations

import pytest

from rescs import cli

RESCS_ENVIRONMENT = (
    "RESCS_API_KEY",
    "RESCS_DATABASE_URL",
    "RESCS_STORAGE_DIR",
    "RESCS_ENV",
    "RESCS_LOG_LEVEL",
)


@pytest.fixture()
def clean_environment(monkeypatch):
    """Simulate a first run with no configuration anywhere."""
    for name in RESCS_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)


def test_doctor_without_configuration_reports_setup_hint(tmp_path, capsys, clean_environment):
    config = tmp_path / "missing.env"

    assert cli.main(["--config", str(config), "doctor"]) == 2

    captured = capsys.readouterr()
    assert "RESCS configuration is invalid" in captured.err
    assert "api_key" in captured.err
    assert "rescs setup" in captured.err


def test_doctor_succeeds_after_setup(tmp_path, capsys, clean_environment):
    config = tmp_path / "rescs.env"

    assert cli.main(["--config", str(config), "setup"]) == 0
    assert cli.main(["--config", str(config), "doctor"]) == 0

    assert "passed" in capsys.readouterr().out


def test_setup_preserves_an_existing_configuration(tmp_path, capsys, clean_environment):
    config = tmp_path / "rescs.env"

    assert cli.main(["--config", str(config), "setup"]) == 0
    original = config.read_text()

    assert cli.main(["--config", str(config), "setup"]) == 0

    assert config.read_text() == original
    assert "preserved" in capsys.readouterr().out


def test_remote_listening_requires_explicit_opt_in(tmp_path, clean_environment):
    config = tmp_path / "rescs.env"

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--config", str(config), "--host", "0.0.0.0", "doctor"])

    assert excinfo.value.code == 2
