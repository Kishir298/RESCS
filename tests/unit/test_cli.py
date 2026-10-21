import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from rescs import cli


@pytest.mark.parametrize("platform,env,expected", [
    ("win32", {"LOCALAPPDATA": "/local"}, "/local/RESCS"),
    ("darwin", {}, "/home/Library/Application Support/RESCS"),
    ("linux", {"XDG_DATA_HOME": "/data"}, "/data/rescs"),
    ("linux", {}, "/home/.local/share/rescs"),
])
def test_platform_directories(platform, env, expected):
    assert cli.data_directory(platform, env, "/home") == Path(expected)


def test_setup_private_idempotent_and_no_secret_output(tmp_path, capsys):
    config = tmp_path / "settings.env"
    cli.setup(config)
    content = config.read_text()
    cli.setup(config)
    assert config.read_text() == content
    assert content.split("RESCS_API_KEY=")[1].strip() not in capsys.readouterr().out
    if os.name != "nt": assert config.stat().st_mode & 0o077 == 0


def test_daily_command_has_stable_paths_and_preserves_remote_settings(tmp_path, monkeypatch):
    for key in ["RESCS_DATABASE_URL", "RESCS_STORAGE_DIR"]: monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(cli, "data_directory", lambda: tmp_path)
    config = tmp_path / "settings.env"
    cli.setup(config)
    first = cli.load_settings(config)
    other = tmp_path / "unrelated"
    other.mkdir()
    (other / ".env").write_text("RESCS_DATABASE_URL=sqlite:///unwanted.db\n")
    monkeypatch.chdir(other)
    second = cli.load_settings(config)
    assert second.database_url == first.database_url == "sqlite:///" + (tmp_path / "rescs.sqlite3").as_posix()
    monkeypatch.setenv("RESCS_DATABASE_URL", "postgresql+psycopg://user:secret@remote.invalid/db")
    assert cli.load_settings(config).database_url.startswith("postgresql+")


def test_no_arguments_starts_loopback_service(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "data_directory", lambda: tmp_path)
    monkeypatch.delenv("RESCS_DATABASE_URL", raising=False)
    monkeypatch.delenv("RESCS_STORAGE_DIR", raising=False)
    calls = []
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=lambda app, **kwargs: calls.append((app, kwargs))))
    assert cli.main([]) == 0
    assert calls[0][1] == {"host": "127.0.0.1", "port": 8081}
    assert calls[0][0].state.settings.database_url.endswith("rescs.sqlite3")


def test_remote_host_requires_explicit_opt_in():
    with pytest.raises(SystemExit) as exc:
        cli.main(["--host", "0.0.0.0"])
    assert exc.value.code == 2


def test_config_errors_do_not_echo_secrets(tmp_path, capsys):
    config = tmp_path / "bad.env"
    config.write_text("RESCS_API_KEY=short\nRESCS_DATABASE_URL=postgresql://user:never-print@host/db\n")
    assert cli.main(["--config", str(config), "doctor"]) == 2
    assert "never-print" not in capsys.readouterr().err
