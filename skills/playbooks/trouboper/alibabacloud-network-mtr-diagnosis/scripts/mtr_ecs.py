"""
mtr_ecs.py - Alibaba Cloud Cloud Assistant remote MTR diagnosis

Remotely execute mtr/ping/curl diagnostic commands on ECS instances via Cloud Assistant (run-command).
"""

import sys
import os
import json
import time
import base64

# Add scripts directory to path for importing mtr_common
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mtr_common import _run_cli, _call_with_retry


# --- Cloud Assistant status check -------------------------------------

def check_cloud_assistant_status(instance_id: str, region: str) -> dict:
    """
    Check whether the Cloud Assistant agent is installed and running on the ECS instance.

    Returns:
        dict: {
            "instance_id": str,
            "installed": bool,
            "agent_status": str,  # "true"/"false" indicating agent online status
            "os_type": str,
            "error": str (if any)
        }
    """
    resp = _call_with_retry("ecs", "describe-cloud-assistant-status", {
        "instance-id": instance_id,
        "biz-region-id": region,
    }, region=region)

    if "error" in resp:
        return {
            "instance_id": instance_id,
            "installed": False,
            "agent_status": "unknown",
            "os_type": "",
            "error": resp["error"],
        }

    statuses = resp.get("InstanceCloudAssistantStatusSet", {}).get(
        "InstanceCloudAssistantStatus", [])

    if not statuses:
        return {
            "instance_id": instance_id,
            "installed": False,
            "agent_status": "not_found",
            "os_type": "",
            "error": f"Cloud Assistant status not found for instance {instance_id}. "
                     f"The instance may not exist or Cloud Assistant is not installed. "
                     f"Install via: aliyun ecs install-cloud-assistant --instance-id {instance_id} --region-id {region}",
        }

    status = statuses[0]
    agent_status = status.get("CloudAssistantStatus", "false")
    os_type = status.get("OSType", "")

    return {
        "instance_id": instance_id,
        "installed": agent_status == "true",
        "agent_status": agent_status,
        "os_type": os_type,
        "error": "" if agent_status == "true" else
                 f"Cloud Assistant agent is not running (status={agent_status}). "
                 f"Please ensure Cloud Assistant is installed and started: "
                 f"https://help.aliyun.com/document_detail/64921.html",
    }


# --- Remote command execution -----------------------------------------

def run_remote_command(instance_id: str, region: str,
                       script_content: str, timeout: int = 120) -> dict:
    """
    Execute a Shell script on ECS via Cloud Assistant.

    Args:
        instance_id: ECS instance ID
        region: Region ID
        script_content: Shell script content
        timeout: Command timeout in seconds

    Returns:
        dict: {
            "invoke_id": str,
            "status": "Finished"|"Failed"|"Timeout"|"Error",
            "stdout": str,
            "stderr": str,
            "exit_code": int,
            "error": str (if any)
        }
    """
    # Base64-encode script content
    encoded_script = base64.b64encode(script_content.encode("utf-8")).decode("utf-8")

    resp = _run_cli("ecs", "run-command", {
        "type": "RunShellScript",
        "command-content": encoded_script,
        "instance-id": instance_id,
        "timeout": str(timeout),
        "content-encoding": "Base64",
    }, region=region, timeout=30)

    if "error" in resp:
        return {
            "invoke_id": "",
            "status": "Error",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "error": resp["error"],
        }

    invoke_id = resp.get("InvokeId", "")
    if not invoke_id:
        return {
            "invoke_id": "",
            "status": "Error",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "error": f"run-command did not return invoke-id, response: {json.dumps(resp, ensure_ascii=False)[:200]}",
        }

    # Poll for results
    return poll_invocation_result(invoke_id, region, max_wait=timeout + 30)


def poll_invocation_result(invoke_id: str, region: str,
                           max_wait: int = 150, interval: int = 5) -> dict:
    """
    Poll Cloud Assistant command execution results.

    Args:
        invoke_id: Command invocation ID
        region: Region ID
        max_wait: Maximum wait time in seconds
        interval: Polling interval in seconds

    Returns:
        dict: {
            "invoke_id": str,
            "status": str,
            "stdout": str,
            "stderr": str,
            "exit_code": int,
            "error": str (if any)
        }
    """
    start_time = time.time()

    while time.time() - start_time < max_wait:
        resp = _run_cli("ecs", "describe-invocation-results", {
            "invoke-id": invoke_id,
        }, region=region)

        if "error" in resp:
            return {
                "invoke_id": invoke_id,
                "status": "Error",
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "error": resp["error"],
            }

        results = resp.get("Invocation", {}).get("InvocationResults", {}).get(
            "InvocationResult", [])

        if not results:
            time.sleep(interval)
            continue

        result = results[0]
        status = result.get("InvocationStatus", result.get("InvokeRecordStatus", ""))

        # Check for terminal status
        if status in ("Finished", "Failed", "Stopped", "Timeout",
                       "PartialFailed", "Success"):
            # Decode Output (base64-encoded)
            raw_output = result.get("Output", "")
            stdout = ""
            if raw_output:
                try:
                    stdout = base64.b64decode(raw_output).decode("utf-8", errors="replace")
                except Exception:
                    stdout = raw_output

            # Decode ErrorInfo
            error_info = result.get("ErrorInfo", "")

            exit_code = result.get("ExitCode", -1)

            return {
                "invoke_id": invoke_id,
                "status": status,
                "stdout": stdout,
                "stderr": error_info,
                "exit_code": exit_code,
                "error": "" if status in ("Finished", "Success") else
                         f"Command execution status: {status}, ErrorInfo: {error_info}",
            }

        # Still running
        time.sleep(interval)

    return {
        "invoke_id": invoke_id,
        "status": "Timeout",
        "stdout": "",
        "stderr": "",
        "exit_code": -1,
        "error": f"Polling timed out (waited {max_wait}s), command may still be running. InvokeId: {invoke_id}",
    }


# --- mtr tool check and installation ---------------------------------

def check_mtr_installed(instance_id: str, region: str) -> dict:
    """
    Check whether the mtr tool is installed on the ECS instance.

    Returns:
        dict: {
            "instance_id": str,
            "installed": bool,
            "mtr_path": str,    # mtr path (when installed)
            "os_type": str,     # "yum" | "apt" | "unknown"
            "error": str
        }
    """
    check_script = "\n".join([
        "#!/bin/bash",
        "# Check whether mtr is installed",
        'MTR_PATH=$(which mtr 2>/dev/null || true)',
        'if [ -n "$MTR_PATH" ]; then',
        '  echo "INSTALLED:$MTR_PATH"',
        "else",
        '  echo "NOT_INSTALLED"',
        "fi",
        "# Detect package manager type",
        "if which yum >/dev/null 2>&1; then",
        '  echo "PKG_MGR:yum"',
        "elif which apt-get >/dev/null 2>&1; then",
        '  echo "PKG_MGR:apt"',
        "else",
        '  echo "PKG_MGR:unknown"',
        "fi",
    ])

    result = run_remote_command(instance_id, region, check_script, timeout=30)

    if result["status"] not in ("Finished", "Success"):
        return {
            "instance_id": instance_id,
            "installed": False,
            "mtr_path": "",
            "os_type": "unknown",
            "error": result.get("error", ""),
        }

    stdout = result["stdout"]
    installed = False
    mtr_path = ""
    os_type = "unknown"

    for line in stdout.strip().splitlines():
        line = line.strip()
        if line.startswith("INSTALLED:"):
            installed = True
            mtr_path = line.split(":", 1)[1]
        elif line == "NOT_INSTALLED":
            installed = False
        elif line.startswith("PKG_MGR:"):
            os_type = line.split(":", 1)[1]

    return {
        "instance_id": instance_id,
        "installed": installed,
        "mtr_path": mtr_path,
        "os_type": os_type,
        "error": "",
    }


def install_mtr(instance_id: str, region: str, pkg_mgr: str = "") -> dict:
    """
    Install the mtr tool on the ECS instance. Requires explicit user authorization before calling.

    Args:
        instance_id: ECS instance ID
        region: Region ID
        pkg_mgr: Package manager type ("yum"|"apt"), auto-detect if empty

    Returns:
        dict: {
            "instance_id": str,
            "installed": bool,
            "mtr_path": str,
            "error": str
        }
    """
    if pkg_mgr == "yum":
        install_cmd = "yum install -y mtr"
    elif pkg_mgr == "apt":
        install_cmd = "apt-get update -qq && apt-get install -y mtr"
    else:
        install_cmd = (
            "if which yum >/dev/null 2>&1; then "
            "yum install -y mtr; "
            "elif which apt-get >/dev/null 2>&1; then "
            "apt-get update -qq && apt-get install -y mtr; "
            "else "
            "echo 'ERROR: no supported package manager found'; exit 1; "
            "fi"
        )

    install_script = "\n".join([
        "#!/bin/bash",
        "set -e",
        f"{install_cmd}",
        "# Verify installation result",
        'MTR_PATH=$(which mtr 2>/dev/null || true)',
        'if [ -n "$MTR_PATH" ]; then',
        '  echo "INSTALL_OK:$MTR_PATH"',
        "else",
        '  echo "INSTALL_FAILED"',
        "  exit 1",
        "fi",
    ])

    result = run_remote_command(instance_id, region, install_script, timeout=120)

    if result["status"] not in ("Finished", "Success"):
        return {
            "instance_id": instance_id,
            "installed": False,
            "mtr_path": "",
            "error": result.get("error", f"Installation failed: {result['stdout']}"),
        }

    stdout = result["stdout"]
    for line in stdout.strip().splitlines():
        line = line.strip()
        if line.startswith("INSTALL_OK:"):
            return {
                "instance_id": instance_id,
                "installed": True,
                "mtr_path": line.split(":", 1)[1],
                "error": "",
            }

    return {
        "instance_id": instance_id,
        "installed": False,
        "mtr_path": "",
        "error": f"mtr still not detected after installation. Output: {stdout[:200]}",
    }


# --- MTR diagnosis wrapper -------------------------------------------

def _build_mtr_script(target: str, count: int = 100,
                      tcp_port: int = None) -> str:
    """Build the MTR diagnostic script for remote execution."""
    lines = [
        "#!/bin/bash",
        "set -e",
        "",
        "# Check mtr availability (installation is handled by the install-mtr subcommand separately)",
        "if ! which mtr >/dev/null 2>&1; then",
        '  echo "ERROR: mtr is not installed. Please use the install-mtr subcommand first."',
        "  exit 1",
        "fi",
        "",
        "# ICMP MTR",
        'echo "===ICMP_MTR_START==="',
        f"mtr -r -c {count} -n {target}",
        'echo "===ICMP_MTR_END==="',
        "",
    ]

    if tcp_port:
        lines.extend([
            "# TCP MTR",
            'echo "===TCP_MTR_START==="',
            f"mtr --tcp -P {tcp_port} -r -c {count} {target}",
            'echo "===TCP_MTR_END==="',
            "",
        ])

    lines.extend([
        "# Ping test",
        'echo "===PING_START==="',
        f"ping -c 20 {target} 2>&1 || true",
        'echo "===PING_END==="',
        "",
    ])

    if tcp_port:
        lines.extend([
            "# Curl test (HTTP)",
            'echo "===CURL_START==="',
            f"curl -o /dev/null -s -w 'HTTP_CODE=%{{http_code}} TIME=%{{time_total}}s CONNECT=%{{time_connect}}s' "
            f"--connect-timeout 10 --max-time 30 http://{target}:{tcp_port}/ 2>&1 || true",
            'echo "===CURL_END==="',
        ])

    return "\n".join(lines)


def _parse_sections(stdout: str) -> dict:
    """Extract sections from marker-delimited output."""
    sections = {}
    markers = [
        ("icmp_mtr", "===ICMP_MTR_START===", "===ICMP_MTR_END==="),
        ("tcp_mtr", "===TCP_MTR_START===", "===TCP_MTR_END==="),
        ("ping", "===PING_START===", "===PING_END==="),
        ("curl", "===CURL_START===", "===CURL_END==="),
    ]

    for name, start_marker, end_marker in markers:
        start_idx = stdout.find(start_marker)
        end_idx = stdout.find(end_marker)
        if start_idx != -1 and end_idx != -1:
            content = stdout[start_idx + len(start_marker):end_idx].strip()
            sections[name] = content
        else:
            sections[name] = ""

    return sections


def run_mtr(instance_id: str, region: str, target: str,
            count: int = 100, tcp_port: int = None) -> dict:
    """
    Execute MTR diagnostics on an ECS instance.

    Args:
        instance_id: ECS instance ID
        region: Region ID
        target: Target IP or domain
        count: Number of MTR probe packets
        tcp_port: TCP port (optional; if specified, TCP MTR is also executed)

    Returns:
        dict: {
            "instance_id": str,
            "target": str,
            "status": str,
            "icmp_mtr": str,
            "tcp_mtr": str,
            "ping": str,
            "curl": str,
            "raw_output": str,
            "error": str
        }
    """
    script = _build_mtr_script(target, count, tcp_port)

    # Timeout = MTR run time + buffer
    timeout = max(count * 2 + 30, 120)
    result = run_remote_command(instance_id, region, script, timeout=timeout)

    if result["status"] not in ("Finished", "Success"):
        return {
            "instance_id": instance_id,
            "target": target,
            "status": result["status"],
            "icmp_mtr": "",
            "tcp_mtr": "",
            "ping": "",
            "curl": "",
            "raw_output": result["stdout"],
            "error": result.get("error", ""),
        }

    sections = _parse_sections(result["stdout"])

    return {
        "instance_id": instance_id,
        "target": target,
        "status": "ok",
        "icmp_mtr": sections.get("icmp_mtr", ""),
        "tcp_mtr": sections.get("tcp_mtr", ""),
        "ping": sections.get("ping", ""),
        "curl": sections.get("curl", ""),
        "raw_output": result["stdout"],
        "error": "",
    }


# --- CLI entry point --------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cloud Assistant remote MTR diagnosis")
    sub = parser.add_subparsers(dest="action")

    # check-agent
    p_check = sub.add_parser("check-agent", help="Check Cloud Assistant agent status")
    p_check.add_argument("--instance-id", required=True, help="ECS instance ID")
    p_check.add_argument("--region", required=True, help="Region ID")

    # check-mtr
    p_check_mtr = sub.add_parser("check-mtr", help="Check whether mtr is installed on ECS")
    p_check_mtr.add_argument("--instance-id", required=True, help="ECS instance ID")
    p_check_mtr.add_argument("--region", required=True, help="Region ID")

    # install-mtr
    p_install = sub.add_parser("install-mtr", help="Install mtr on ECS (requires user authorization)")
    p_install.add_argument("--instance-id", required=True, help="ECS instance ID")
    p_install.add_argument("--region", required=True, help="Region ID")
    p_install.add_argument("--pkg-mgr", default="", help="Package manager (yum|apt), auto-detect if empty")

    # run-mtr
    p_mtr = sub.add_parser("run-mtr", help="Remotely execute MTR diagnosis")
    p_mtr.add_argument("--instance-id", required=True, help="ECS instance ID")
    p_mtr.add_argument("--region", required=True, help="Region ID")
    p_mtr.add_argument("--target", required=True, help="Target IP or domain")
    p_mtr.add_argument("--count", type=int, default=100, help="Number of MTR probe packets")
    p_mtr.add_argument("--tcp-port", type=int, default=None, help="TCP port (optional)")

    # run-command (raw command execution)
    p_cmd = sub.add_parser("run-command", help="Remotely execute custom script")
    p_cmd.add_argument("--instance-id", required=True, help="ECS instance ID")
    p_cmd.add_argument("--region", required=True, help="Region ID")
    p_cmd.add_argument("--script", required=True, help="Shell script content")
    p_cmd.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")

    # poll (manual polling)
    p_poll = sub.add_parser("poll", help="Poll command execution results")
    p_poll.add_argument("--invoke-id", required=True, help="Invocation ID")
    p_poll.add_argument("--region", required=True, help="Region ID")
    p_poll.add_argument("--max-wait", type=int, default=150, help="Maximum wait time in seconds")

    args = parser.parse_args()

    if args.action == "check-agent":
        result = check_cloud_assistant_status(args.instance_id, args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "check-mtr":
        result = check_mtr_installed(args.instance_id, args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "install-mtr":
        result = install_mtr(args.instance_id, args.region, args.pkg_mgr)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "run-mtr":
        result = run_mtr(args.instance_id, args.region, args.target,
                         args.count, args.tcp_port)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "run-command":
        result = run_remote_command(args.instance_id, args.region,
                                    args.script, args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "poll":
        result = poll_invocation_result(args.invoke_id, args.region,
                                        args.max_wait)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
