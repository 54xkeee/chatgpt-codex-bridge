#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/bridge/codex-mcp-guard.py"
MIRROR = ROOT / "plugins/chatgpt-codex-bridge/bridge/codex-mcp-guard.py"


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


text = SOURCE.read_text(encoding="utf-8")

text = replace_once(
    text,
    "JOB_CONTROL_POLL_SECONDS = 0.25\nJOB_CANCEL_GRACE_SECONDS = 1.5\nJOB_CONTROL_MAX_ITEMS = 100\n",
    "JOB_CONTROL_POLL_SECONDS = 0.25\nJOB_CANCEL_GRACE_SECONDS = 0.75\nJOB_CANCEL_WORKER_WAIT_SECONDS = 0.75\nJOB_CONTROL_MAX_ITEMS = 100\n",
    "cancel timing constants",
)

# os.kill(pid, 0) reports POSIX zombies as existing. For lifecycle ownership we
# care whether the worker can still execute/write, so treat a Linux zombie as
# stopped and reap it below when this bridge process is its parent.
text = replace_once(
    text,
    '''    try:\n        os.kill(pid, 0)\n    except ProcessLookupError:\n        return False\n    except PermissionError:\n        return True\n    return True\n''',
    '''    proc_stat = Path(f"/proc/{pid}/stat")\n    try:\n        raw_stat = proc_stat.read_text(encoding="utf-8", errors="replace")\n        right_paren = raw_stat.rfind(")")\n        if right_paren >= 0:\n            fields = raw_stat[right_paren + 2 :].split()\n            if fields and fields[0] == "Z":\n                return False\n    except OSError:\n        pass\n    try:\n        os.kill(pid, 0)\n    except ProcessLookupError:\n        return False\n    except PermissionError:\n        return True\n    return True\n''',
    "zombie-aware process probe",
)

# Reap the worker when cancellation is running in the original bridge parent.
# A separate revoke process is not the parent and simply gets ChildProcessError.
text = replace_once(
    text,
    '''    if process_exists(pid):\n        raise GuardProtocolError("managed worker did not stop")\n    return True\n''',
    '''    if process_exists(pid):\n        raise GuardProtocolError("managed worker did not stop")\n    if os.name != "nt":\n        try:\n            os.waitpid(pid, os.WNOHANG)\n        except (ChildProcessError, OSError):\n            pass\n    return True\n''',
    "cancel worker reap",
)

call = "            terminate_verified_job_worker(path)\n"
if text.count(call) != 2:
    raise SystemExit(
        f"cancel worker calls: expected two anchors, found {text.count(call)}"
    )
text = text.replace(
    call,
    "            terminate_verified_job_worker(\n                path, wait_seconds=JOB_CANCEL_WORKER_WAIT_SECONDS\n            )\n",
)

SOURCE.write_text(text, encoding="utf-8")
MIRROR.write_text(text, encoding="utf-8")
