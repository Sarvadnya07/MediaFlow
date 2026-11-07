import subprocess
import json
import pytest
import sys
from pathlib import Path

# Path to python in current virtual environment
PYTHON_EXE = sys.executable

def test_sidecar_ipc_stdio_handshake():
    """Verify that Python sidecar launches, communicates via JSONL, and shuts down cleanly."""
    proc = subprocess.Popen(
        [PYTHON_EXE, "-m", "app.engine.sidecar"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # 1. Initialize
    init_cmd = json.dumps({"id": "test-init", "action": "initialize", "payload": {}}) + "\n"
    proc.stdin.write(init_cmd)
    proc.stdin.flush()

    line = proc.stdout.readline()
    resp = json.loads(line)
    assert resp["id"] == "test-init"
    assert resp["status"] == "success"
    assert resp["data"]["status"] == "ready"

    # 2. Health check
    health_cmd = json.dumps({"id": "test-health", "action": "health_check", "payload": {}}) + "\n"
    proc.stdin.write(health_cmd)
    proc.stdin.flush()

    line = proc.stdout.readline()
    resp = json.loads(line)
    assert resp["id"] == "test-health"
    assert resp["status"] == "success"
    assert "dependencies" in resp["data"]

    # 3. Shutdown
    shutdown_cmd = json.dumps({"id": "test-shutdown", "action": "shutdown", "payload": {}}) + "\n"
    proc.stdin.write(shutdown_cmd)
    proc.stdin.flush()

    line = proc.stdout.readline()
    resp = json.loads(line)
    assert resp["id"] == "test-shutdown"
    assert resp["status"] == "success"

    proc.wait(timeout=5)
    assert proc.returncode == 0
