#!/usr/bin/env python3
"""Start one guarded helper and observe it without restarting or long blocking calls."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timezone


SCRIPTS = Path(__file__).resolve().parent


def now():
    return datetime.now(timezone.utc).isoformat()


def save(job, name, value):
    temporary = job / (name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False) + "\n")
    temporary.replace(job / name)


def session_id(job):
    path = job / "stderr"
    if not path.exists():
        return None
    match = re.search(
        r"^\[SessionID\] ([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})$",
        path.read_text(errors="replace"), re.MULTILINE,
    )
    return match.group(1) if match else None


def worker(job, query, prepare, options):
    """The worker invokes the existing helper once; it never retries a job."""
    os.umask(0o077)
    phase = "prepare" if prepare else "agent"
    result = {"state": "running", "phase": phase, "started_at": now()}
    try:
        save(job, "status.json", result)
        if prepare:
            with (job / "setup.stdout").open("wb") as out, (job / "setup.stderr").open("wb") as err:
                code = subprocess.run(
                    ["bash", str(SCRIPTS / "prepare_apsaradb_agent.sh")],
                    stdin=subprocess.DEVNULL, stdout=out, stderr=err, check=False,
                ).returncode
            if code:
                result.update(state="finished", exit_code=code, finished_at=now())
                save(job, "status.json", result)
                return
        result.update(phase="agent", query_started_at=now())
        save(job, "status.json", result)
        with query.open("rb") as inp, (job / "stdout").open("wb") as out, (job / "stderr").open("wb") as err:
            code = subprocess.run(
                ["bash", str(SCRIPTS / "call_apsaradb_agent.sh"), "-", *options],
                stdin=inp, stdout=out, stderr=err, check=False,
            ).returncode
        # The streams are closed before publishing terminal state.
        result.update(state="finished", exit_code=code, finished_at=now())
    except Exception as error:
        # Do not echo queries, arguments or environment values in an error.
        result.update(state="finished", exit_code=1, error=type(error).__name__, finished_at=now())
    save(job, "status.json", result)


def process_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    stat = Path(f"/proc/{pid}/stat")
    try:
        if stat.exists() and stat.read_text().rsplit(") ", 1)[-1].startswith("Z"):
            return False
    except FileNotFoundError:
        return False
    return True


def status(job):
    path = job / "status.json"
    result = json.loads(path.read_text()) if path.exists() else {"state": "running", "phase": "starting"}
    if result["state"] != "finished":
        pid = int((job / "pid").read_text())
        if not process_alive(pid):
            result.update(state="interrupted", error="Worker exited without a terminal status; do not relaunch")
    result["job_dir"] = str(job)
    for name in ("stdout", "stderr"):
        path = job / name
        result[name + "_bytes"] = path.stat().st_size if path.exists() else 0
    result["session_id"] = session_id(job)
    result["request_succeeded"] = (
        result["state"] == "finished" and result.get("phase") == "agent"
        and result.get("exit_code") == 0 and result["stdout_bytes"] > 0
        and result["session_id"] is not None
        and bool((job / "stdout").read_text(errors="replace").strip())
    )
    return result


def start(args):
    job, query = Path(args.job_dir), Path(args.query_file)
    if not job.is_absolute() or not query.is_absolute():
        raise ValueError("Use absolute job and query paths")
    content = query.read_bytes()
    if not content.strip():
        raise ValueError("The query file is empty")
    os.umask(0o077)
    job.mkdir(mode=0o700, parents=True)  # Exclusive: an existing job never starts another request.
    options = args.options[1:] if args.options[:1] == ["--"] else args.options
    save(job, "request.json", {
        "created_at": now(), "query_sha256": hashlib.sha256(content).hexdigest(),
    })
    with (job / "worker.stdout").open("wb") as out, (job / "worker.stderr").open("wb") as err:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "_worker", str(job), str(query),
             "yes" if args.prepare else "no", *options],
            stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True,
        )
    (job / "pid").write_text(str(process.pid) + "\n")
    return status(job)


def main():
    if sys.argv[1:2] == ["_worker"]:
        worker(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4] == "yes", sys.argv[5:])
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    launch = commands.add_parser("start", help="Start once; launch success is not query success")
    launch.add_argument("--job-dir", required=True)
    launch.add_argument("--query-file", required=True)
    launch.add_argument("--prepare", action="store_true", help="Run authorized standard dependency preparation")
    launch.add_argument("options", nargs=argparse.REMAINDER)
    for action in ("wait", "result"):
        command = commands.add_parser(action)
        command.add_argument("--job-dir", required=True)
        command.add_argument("--seconds", type=int, default=30 if action == "wait" else 0)
    args = parser.parse_args()
    try:
        if args.command == "start":
            result = start(args)
        else:
            job = Path(args.job_dir)
            if not job.is_absolute():
                raise ValueError("Use an absolute job path")
            seconds = getattr(args, "seconds", 0)
            if not 0 <= seconds <= 55:
                raise ValueError("Wait duration must be between 0 and 55 seconds")
            deadline = time.monotonic() + seconds
            result = status(job)
            while result["state"] == "running" and time.monotonic() < deadline:
                time.sleep(min(0.2, max(0, deadline - time.monotonic())))
                result = status(job)
            if args.command == "result":
                if result["state"] != "finished":
                    raise ValueError("The job has not finished; observe the same job, do not start another")
                error_file = "setup.stderr" if result.get("phase") == "prepare" else "stderr"
                if (job / error_file).exists():
                    sys.stderr.write((job / error_file).read_text(errors="replace"))
                if result["request_succeeded"]:
                    sys.stdout.write((job / "stdout").read_text(errors="replace"))
                    return 0
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
        return 1 if result["state"] == "interrupted" or (result["state"] == "finished" and not result["request_succeeded"]) else 0
    except (OSError, ValueError, KeyError) as error:
        sys.stderr.write(f"Job error ({type(error).__name__}); check the job path and existing logs. No job was restarted.\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
