"""Real installed command smoke from an unrelated directory; no external service needed."""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request


def main():
    command = shutil.which("rescs")
    if not command:
        raise RuntimeError("Install RESCS and place its Scripts/bin directory on PATH")
    env = {key: value for key, value in os.environ.items() if not key.startswith("RESCS_")}
    with tempfile.TemporaryDirectory(prefix="rescs-smoke-") as directory:
        root = Path(directory)
        key = secrets.token_urlsafe(32)
        config = root / "test.env"
        config.write_text("RESCS_API_KEY=" + key + "\nRESCS_DATABASE_URL=sqlite:///" + (root / "records.db").as_posix() + "\nRESCS_STORAGE_DIR=" + (root / "files").as_posix() + "\n", encoding="utf-8")
        if os.name != "nt": config.chmod(0o600)
        subprocess.run([command, "--help"], cwd=root, env=env, check=True, capture_output=True)
        subprocess.run([command, "--config", str(config), "doctor"], cwd=root, env=env, check=True, capture_output=True)
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        log = root / "server.log"
        with log.open("wb") as stream:
            process = subprocess.Popen([command, "--config", str(config), "--port", str(port)], cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT)
            try:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                def request(path, body=None):
                    data = json.dumps(body).encode() if body is not None else None
                    req = urllib.request.Request(f"http://127.0.0.1:{port}" + path, data=data, method="PUT" if data else "GET", headers={"X-API-Key": key, "Content-Type": "application/json"})
                    with opener.open(req, timeout=2) as response:
                        return json.load(response)
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Installed RESCS exited before readiness; inspect dependencies and configuration")
                    try:
                        ready = request("/health/ready")
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Installed RESCS readiness timeout")
                assert ready
                saved = request("/api/v1/records", {"owner": "smoke", "namespace": "smoke", "key": "key", "value": {"real": True}})
                page = request("/api/v1/records?owner=smoke&namespace=smoke&limit=1&offset=0")
                assert page["total"] == 1 and page["items"][0]["id"] == saved["id"]
                print("Installed command: real loopback startup, readiness, upsert and listing passed.")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()
