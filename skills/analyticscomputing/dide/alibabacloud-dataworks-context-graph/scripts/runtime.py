#!/usr/bin/env python3
"""Check the local runtime offline or prepare pinned dependencies in a dedicated venv."""

import argparse
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

from context_graph_auth import credential_shape, read_credentials_file
from context_graph_contract import SkillError, endpoint_allowlist, resolve_endpoint
from context_graph_cli_transport import authentication_environment, inspect_cli, validate_backend


REQUIREMENTS = Path(__file__).with_name("requirements.txt")
MINIMUM_PYTHON = (3, 10)
RUNTIME_OWNER = {"tool": "alibabacloud-dataworks-context-graph", "schema_version": 1}
PROBE = """import json, platform, sys
from importlib import metadata
print(json.dumps({"version": list(sys.version_info[:3]), "platform": platform.system(),
"prefix": sys.prefix, "base_prefix": sys.base_prefix,
"packages": {d.metadata["Name"].lower().replace("_", "-"): d.version for d in metadata.distributions() if d.metadata["Name"]}}))
"""


def active_requirements(version, system, path=REQUIREMENTS):
    """Support only current bounded requirement markers; reject unknown expressions without eval."""
    required = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_-]+)==([A-Za-z0-9.]+)(?:;\s*(.*))?', line)
        if not match:
            raise SkillError("RequirementsInvalid", "The pinned requirements file contains an unsupported format.")
        name, pin, marker = match.groups()
        enabled = True
        if marker:
            python_marker = re.fullmatch(r'python_version < "(\d+)\.(\d+)"', marker)
            if python_marker:
                enabled = tuple(version[:2]) < tuple(map(int, python_marker.groups()))
            elif marker == 'platform_system == "Windows"':
                enabled = system == "Windows"
            else:
                raise SkillError("RequirementsInvalid", "The pinned requirements file contains an unsupported marker.")
        if enabled:
            key = name.lower().replace("_", "-")
            if key in required:
                raise SkillError("RequirementsInvalid", "The pinned requirements file contains duplicate packages.")
            required[key] = pin
    return required


def dependencies(info):
    required = active_requirements(info["version"], info["platform"])
    found = info["packages"]
    missing = sorted(name for name in required if name not in found)
    mismatched = [{"Package": name, "Required": pin, "Installed": found[name]}
                  for name, pin in sorted(required.items()) if name in found and found[name] != pin]
    return {"Ready": not missing and not mismatched, "RequiredCount": len(required),
            "Missing": missing, "Mismatched": mismatched}


def local_info():
    return {"version": list(sys.version_info[:3]), "platform": platform.system(),
            "packages": {d.metadata["Name"].lower().replace("_", "-"): d.version
                         for d in metadata.distributions() if d.metadata["Name"]}}


def doctor(region, credentials_file=None, *, backend="sdk", profile=None):
    # Do not read stdin or ask callers to resupply an existing session credential triple.
    validate_backend(backend, profile)
    if profile is not None and credentials_file is not None:
        raise SkillError("InvalidParameter", "A CLI profile cannot be combined with an explicit credentials file.")
    environment = dict(os.environ)
    resolve_endpoint(region, environment.get("DATAWORKS_ENDPOINT"), allowed_hosts=endpoint_allowlist(environment))
    if credentials_file is not None:
        environment.update(read_credentials_file(credentials_file))
    shape = credential_shape(environment)
    if backend == "aliyun":
        child_environment, mode = authentication_environment(environment, profile)
        cli = inspect_cli(child_environment)
        supported = sys.version_info[:2] >= MINIMUM_PYTHON
        return {"Success": supported, "RuntimeReady": supported, "Backend": "aliyun",
                "Python": {"Version": platform.python_version(), "Supported": supported, "Minimum": "3.10"},
                "AliyunCli": cli, "SdkDependenciesRequired": False,
                "EndpointConfigured": "DATAWORKS_ENDPOINT" in environment, "EndpointValid": True,
                "CredentialsConfigured": mode is not None,
                "CredentialShape": shape if mode is not None else "delegated_profile",
                "AuthenticationSource": "injected_credentials" if mode is not None else "aliyun_profile",
                "LiveAuthVerified": False}
    info = local_info()
    deps = dependencies(info)
    supported = tuple(info["version"][:2]) >= MINIMUM_PYTHON
    ready = supported and deps["Ready"]
    return {"Success": ready and shape != "invalid", "RuntimeReady": ready,
            "Python": {"Version": ".".join(map(str, info["version"])), "Supported": supported,
                       "Minimum": "3.10"}, "Dependencies": deps,
            "EndpointConfigured": "DATAWORKS_ENDPOINT" in environment, "EndpointValid": True,
            "CredentialsConfigured": shape == "configured", "CredentialShape": shape,
            "LiveAuthVerified": False}


def installer_environment():
    # Give installers only required runtime, network, and index settings, not cloud credentials/debug settings.
    allowed = {"PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR", "COMSPEC", "APPDATA", "LOCALAPPDATA",
               "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
               "http_proxy", "https_proxy", "all_proxy", "no_proxy", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE",
               "SSL_CERT_FILE", "SSL_CERT_DIR"}
    pip_network = {"PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "PIP_TRUSTED_HOST", "PIP_CERT", "PIP_CLIENT_CERT",
                   "PIP_PROXY", "PIP_TIMEOUT", "PIP_DEFAULT_TIMEOUT", "PIP_RETRIES", "PIP_NO_INDEX", "PIP_FIND_LINKS"}
    environment = {key: value for key, value in os.environ.items() if key in allowed or key in pip_network}
    # Disable system/user pip configuration so target/prefix/user/log cannot escape the dedicated environment.
    environment["PIP_CONFIG_FILE"] = os.devnull
    environment["PIP_REQUIRE_VIRTUALENV"] = "true"
    return environment


def run_local(arguments, timeout):
    try:
        return subprocess.run(arguments, env=installer_environment(), capture_output=True,
                              text=True, check=False, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        raise SkillError("RuntimePreparationFailed", "Local runtime preparation failed or timed out; check Python, venv, and package-index connectivity.") from None


def probe(executable):
    result = run_local([str(executable), "-I", "-c", PROBE], 20)
    try:
        if result.returncode != 0 or len(result.stdout) > 1024 * 1024:
            return None
        info = json.loads(result.stdout)
        if (not isinstance(info, dict) or not isinstance(info.get("version"), list)
                or len(info["version"]) != 3 or any(type(n) is not int for n in info["version"])
                or not isinstance(info.get("platform"), str) or not isinstance(info.get("packages"), dict)
                or not isinstance(info.get("prefix"), str) or not info["prefix"]
                or not isinstance(info.get("base_prefix"), str) or not info["base_prefix"]):
            return None
        return info
    except (ValueError, TypeError):
        return None


def target_venv(info, target):
    """Verify the actual venv identity; a marker or Python symlink does not prove isolation."""
    return bool(info and (target / "pyvenv.cfg").is_file()
                and Path(info["prefix"]).resolve() == target.resolve()
                and Path(info["prefix"]).resolve() != Path(info["base_prefix"]).resolve())


def module_command(executable, module, *arguments):
    # -I excludes cwd/PYTHONPATH/user site to prevent local venv.py or pip.py module hijacking.
    return [str(executable), "-I", "-m", module, *arguments]


def select_python(explicit=None):
    candidates = [explicit] if explicit is not None else [sys.executable] + [
        shutil.which("python" + version) for version in ("3.14", "3.13", "3.12", "3.11", "3.10")]
    visited = set()
    for executable in candidates:
        if not executable or executable in visited:
            continue
        visited.add(executable)
        try:
            info = probe(executable)
        except SkillError:
            info = None
        if info and tuple(info["version"][:2]) >= MINIMUM_PYTHON:
            return str(executable), info
    raise SkillError("PythonUnavailable", "No existing Python 3.10+ was found; provide --python or configure a suitable Python first. Interpreters are not downloaded automatically.")


def default_runtime_dir():
    cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return cache / "alibabacloud-dataworks-context-graph" / "venv"


def setup(python=None, runtime_dir=None):
    if runtime_dir is not None and not str(runtime_dir).strip():
        raise SkillError("InvalidParameter", "--runtime-dir must be a nonempty dedicated directory path.")
    target = Path(runtime_dir) if runtime_dir is not None else default_runtime_dir()
    if target.is_symlink():
        raise SkillError("RuntimeDirectoryConflict", "The runtime directory cannot be a symlink; specify a dedicated directory.")
    executable = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    managed = target / ".context-graph-runtime.json"
    owned = False
    if managed.is_file():
        try:
            owned = managed.stat().st_size < 1024 and json.loads(managed.read_text()) == RUNTIME_OWNER
        except (OSError, ValueError):
            pass
    if target.exists() and (not target.is_dir() or (any(target.iterdir()) and not owned)):
        raise SkillError("RuntimeDirectoryConflict", "The target contains an environment not owned by this tool; specify an empty dedicated directory. Existing files are not overwritten.")
    selected = select_python(python) if python is not None else None
    if executable.is_file() and owned:
        info = probe(executable)
        if not target_venv(info, target):
            raise SkillError("RuntimeDirectoryConflict", "The cached interpreter is outside the target venv or the environment is damaged; use a new dedicated directory.")
        if info and tuple(info["version"][:2]) >= MINIMUM_PYTHON:
            if selected and selected[1]["version"][:2] != info["version"][:2]:
                raise SkillError("RuntimeDirectoryConflict", "The cached Python version differs from --python; use another dedicated directory.")
            if dependencies(info)["Ready"]:
                return {"Success": True, "RuntimeReady": True, "Reused": True,
                        "Python": str(executable), "LiveAuthVerified": False}
        elif info:
            raise SkillError("RuntimeDirectoryConflict", "The cached Python version is unsupported; use a new dedicated directory.")
    if selected is None:
        selected = select_python()
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.parent / ("." + target.name + ".setup.lock")
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SkillError("RuntimeBusy", "The dedicated runtime is being prepared; retry after completion. Stale locks require manual review and are not overwritten.") from None
    os.close(descriptor)
    try:
        target.mkdir(parents=True, exist_ok=True)
        # Mark tool ownership before installation so partial retries never take over another directory.
        managed.write_text(json.dumps(RUNTIME_OWNER) + "\n")
        if not executable.is_file():
            result = run_local(module_command(selected[0], "venv", str(target)), 60)
            if result.returncode != 0:
                raise SkillError("RuntimePreparationFailed", "Cannot create the dedicated venv; check Python venv/ensurepip support.")
        if not target_venv(probe(executable), target):
            raise SkillError("RuntimeDirectoryConflict", "The target interpreter is not an isolated venv; dependencies will not be installed into base Python.")
        result = run_local(module_command(executable, "pip", "install", "--no-user", "--disable-pip-version-check", "-r", str(REQUIREMENTS)), 300)
        if result.returncode != 0:
            raise SkillError("RuntimePreparationFailed", "Pinned dependency installation failed; check the dedicated environment and package index. Raw installer output was not exposed.")
        info = probe(executable)
        if (not target_venv(info, target) or tuple(info["version"][:2]) < MINIMUM_PYTHON
                or not dependencies(info)["Ready"]):
            raise SkillError("RuntimePreparationFailed", "The dedicated runtime does not satisfy pinned dependencies; check the package index and installation result.")
        return {"Success": True, "RuntimeReady": True, "Reused": False,
                "Python": str(executable), "LiveAuthVerified": False}
    finally:
        lock.unlink()


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError("InvalidParameter", "Invalid local-runtime command arguments; use --help.")


def main(argv=None):
    try:
        root = Parser(description="Check or prepare the local Python runtime without calling DataWorks APIs.", allow_abbrev=False)
        groups = root.add_subparsers(dest="command", required=True, parser_class=Parser)
        check = groups.add_parser("doctor", allow_abbrev=False)
        check.add_argument("--region", required=True)
        check.add_argument("--backend", choices=("sdk", "aliyun"), default="sdk")
        check.add_argument("--profile")
        check.add_argument("--credentials-file")
        prepare = groups.add_parser("setup", allow_abbrev=False)
        prepare.add_argument("--python")
        prepare.add_argument("--runtime-dir")
        args = root.parse_args(argv)
        result = doctor(args.region, args.credentials_file, backend=args.backend, profile=args.profile) if args.command == "doctor" else setup(args.python, args.runtime_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["Success"] else 1
    except SkillError as error:
        print(json.dumps(error.envelope(), ensure_ascii=False, indent=2))
        return 1
    except KeyboardInterrupt:
        print(json.dumps({"Success": False, "Error": {"Code": "Interrupted", "Message": "Local preparation was interrupted.", "Retryable": False}}, ensure_ascii=False))
        return 130
    except Exception:
        print(json.dumps({"Success": False, "Error": {"Code": "RuntimeCheckFailed", "Message": "Local runtime checking or preparation failed.", "Retryable": False}}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
