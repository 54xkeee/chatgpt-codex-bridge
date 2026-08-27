import argparse
import importlib.util
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--guard", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--codex-bin", required=True)
    parser.add_argument("--python-bin", required=True)
    arguments = parser.parse_args()
    workspace = Path(arguments.workspace)
    jobs = workspace / "guard-jobs"
    jobs.mkdir(exist_ok=True)
    command = [
        arguments.python_bin,
        arguments.guard,
        "--workspace", str(workspace),
        "--codex-bin", arguments.codex_bin,
        "--desktop-open-bin", arguments.codex_bin,
        "--job-state-dir", str(jobs),
        "--sandbox", "workspace-write",
        "--approval-policy", "on-request",
    ]
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    def send(message):
        process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        process.stdin.flush()

    def receive():
        line = process.stdout.readline()
        if not line:
            raise AssertionError(process.stderr.read())
        return json.loads(line)

    send({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "windows-port-test", "version": "1"},
        },
    })
    initialized = receive()
    assert initialized["id"] == 1
    assert "tools" in initialized["result"]["capabilities"]
    send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    listed = receive()
    assert [tool["name"] for tool in listed["result"]["tools"]] == [
        "codex",
        "codex-reply",
    ]
    process.stdin.close()
    assert process.wait(timeout=30) == 0
    print("PASS: Windows Guard MCP initialize/tools-list")

    spec = importlib.util.spec_from_file_location("guard_atomic_fixture", arguments.guard)
    guard_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard_module)
    atomic_target = workspace / "atomic-status.json"
    original_replace = guard_module.os.replace
    attempts = {"count": 0}

    def flaky_replace(source, destination):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise PermissionError(5, "fixture contention")
        return original_replace(source, destination)

    guard_module.os.replace = flaky_replace
    try:
        guard_module.atomic_write_json(atomic_target, {"status": "completed"})
    finally:
        guard_module.os.replace = original_replace
    assert attempts["count"] == 3
    assert json.loads(atomic_target.read_text(encoding="utf-8"))["status"] == "completed"
    print("PASS: Windows atomic status replacement retry")

    revoke_root = workspace / "revoke-jobs"
    internal_job_id = str(uuid.uuid4())
    job_dir = revoke_root / internal_job_id
    job_dir.mkdir(parents=True)
    fake_guard = workspace / "codex-mcp-guard.py"
    fake_guard.write_text(
        "import pathlib,subprocess,sys,time\n"
        "job_dir=sys.argv[sys.argv.index('--run-job')+1]\n"
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])\n"
        "pathlib.Path(job_dir,'child.pid').write_text(str(child.pid),encoding='ascii')\n"
        "time.sleep(60)\n",
        encoding="utf-8",
    )
    worker = subprocess.Popen(
        [sys.executable, str(fake_guard), "--run-job", str(job_dir)],
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    (job_dir / "status.json").write_text(json.dumps({
        "internalJobId": internal_job_id,
        "status": "running",
        "content": "",
    }), encoding="utf-8")
    (job_dir / "worker.json").write_text(json.dumps({
        "pid": worker.pid,
        "processGroupId": worker.pid,
        "guardScript": str(fake_guard),
        "jobDir": str(job_dir),
    }), encoding="utf-8")
    child_pid_path = job_dir / "child.pid"
    deadline = time.monotonic() + 5
    while not child_pid_path.is_file() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert child_pid_path.is_file()
    child_pid = int(child_pid_path.read_text(encoding="ascii"))
    revoked = subprocess.run(
        [arguments.python_bin, arguments.guard, "--revoke-jobs", str(revoke_root)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    state = json.loads((job_dir / "status.json").read_text(encoding="utf-8"))
    assert revoked.returncode == 0
    assert state["status"] == "interrupted"
    assert worker.poll() is not None
    assert not guard_module.process_exists(child_pid)
    print("PASS: Windows verified worker-tree revocation")

    cancel_root = workspace / "cancel-jobs"
    store = guard_module.JobStore(
        str(cancel_root),
        arguments.codex_bin,
        str(workspace),
        "danger-full-access",
        "never",
        arguments.codex_bin,
    )
    cancel_internal_id = str(uuid.uuid4())
    cancel_job_id = store.capabilities.encode("job", cancel_internal_id)
    cancel_job_dir = cancel_root / cancel_internal_id
    cancel_job_dir.mkdir()
    execution_token = uuid.uuid4().hex
    cancel_worker = subprocess.Popen(
        [
            sys.executable,
            str(fake_guard),
            "--run-job",
            str(cancel_job_dir),
            "--execution-token",
            execution_token,
        ],
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    (cancel_job_dir / "status.json").write_text(json.dumps({
        "jobId": cancel_job_id,
        "internalJobId": cancel_internal_id,
        "status": "running",
        "pid": cancel_worker.pid,
        "content": "running fixture",
        "updatedAt": time.time(),
    }), encoding="utf-8")
    (cancel_job_dir / "request.json").write_text(json.dumps({
        "jobId": cancel_job_id,
        "internalJobId": cancel_internal_id,
        "executionToken": execution_token,
    }), encoding="utf-8")
    (cancel_job_dir / "worker.json").write_text(json.dumps({
        "pid": cancel_worker.pid,
        "processGroupId": cancel_worker.pid,
        "guardScript": str(fake_guard),
        "jobDir": str(cancel_job_dir),
        "executionToken": execution_token,
    }), encoding="utf-8")
    cancel_child_path = cancel_job_dir / "child.pid"
    deadline = time.monotonic() + 5
    while not cancel_child_path.is_file() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert cancel_child_path.is_file()
    cancel_child_pid = int(cancel_child_path.read_text(encoding="ascii"))
    cancelled = store.cancel(cancel_job_id)
    assert cancelled["status"] == "interrupted"
    assert cancel_worker.poll() is not None
    assert not guard_module.process_exists(cancel_child_pid)
    assert store.cancel(cancel_job_id)["status"] == "interrupted"
    print("PASS: Windows job cancel stops verified worker process tree")


if __name__ == "__main__":
    main()
