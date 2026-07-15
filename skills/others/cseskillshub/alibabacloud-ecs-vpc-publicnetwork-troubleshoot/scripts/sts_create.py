#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Credential Validation & AssumeRole Tool (for customer self-service use)

Validates that Alibaba Cloud SDK default credential chain is properly configured,
or obtains STS temporary credentials via AssumeRole.

The SDK default credential chain resolves credentials automatically from:
  1. Environment variables (ALIBABA_CLOUD_ACCESS_KEY_ID, etc.)
  2. Credentials file (~/.alibabacloud/credentials)
  3. aliyun CLI config (~/.aliyun/config.json)
  4. Instance metadata (ECS RAM Role)

Usage:
    # Validate default credential chain (SDK auto-resolves)
    python sts_create.py

    # Get credentials from aliyun CLI configuration
    python sts_create.py --cli

    # Get STS temporary credentials via AssumeRole
    python sts_create.py --role-arn acs:ram::<UID>:role/<ROLE_NAME>

Security:
  - This tool performs credential validation / STS AssumeRole only; it never
    creates, modifies, deletes, or restarts any cloud resource.
  - Credentials are never printed in plaintext; the local cache
    (scripts/.sts_cache.json) is written with 0o600 (owner-only) permissions
    and is git-ignored to prevent accidental commit to version control.
  - Credentials are read only from the standard Alibaba Cloud SDK credential
    chain (env vars / credentials file / CLI config / ECS RAM role); all
    subprocess calls are invoked as argument lists (never via a shell) with
    validated inputs.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


# STS credential cache file path
STS_CACHE_FILE = Path(__file__).parent / ".sts_cache.json"

# Cache expiry buffer (seconds), to avoid using credentials that are about to expire
CACHE_EXPIRY_BUFFER = 60


# ---------------- Cache Read/Write ----------------

def _read_cache_file() -> dict:
    """
    Read cache file, normalize to:
        {"last_active_uid": "<uid>", "credentials": {"<uid>": {...}}}
    Compatible with old single-entry format. Returns empty structure on read failure/missing.
    """
    empty = {"credentials": {}}
    if not STS_CACHE_FILE.exists():
        return empty

    try:
        with open(STS_CACHE_FILE, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return empty

    if not isinstance(raw, dict):
        return empty

    if isinstance(raw.get('credentials'), dict):
        return {
            "last_active_uid": raw.get('last_active_uid'),
            "credentials": raw['credentials'],
        }

    # Old format compatibility: top-level is a single UID's credentials
    old_uid = raw.get('uid')
    if old_uid and raw.get('access_key_id'):
        entry = {k: v for k, v in raw.items() if k != 'uid'}
        return {"credentials": {str(old_uid): entry}}

    return empty


def _is_credential_valid(entry: dict) -> bool:
    """Check if a cached credential entry is still valid (not expired)"""
    if not isinstance(entry, dict):
        return False
    expiration = entry.get('expiration')
    if not expiration:
        return False
    try:
        expiration_str = expiration.replace('Z', '+00:00')
        try:
            exp_time = datetime.fromisoformat(expiration_str).replace(tzinfo=None)
        except (ValueError, AttributeError):
            exp_time = datetime.strptime(expiration_str[:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return False

    now = datetime.utcnow() + timedelta(seconds=CACHE_EXPIRY_BUFFER)
    return now < exp_time


def _update_last_active_uid(uid: str):
    """Update last_active_uid on cache reuse for downstream scripts to locate."""
    if not uid:
        return
    cache = _read_cache_file()
    if cache.get('last_active_uid') == str(uid):
        return
    cache['last_active_uid'] = str(uid)
    try:
        with open(STS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        os.chmod(STS_CACHE_FILE, 0o600)  # restrict credential cache to owner read/write only
    except OSError:
        pass


def load_cached_credentials(uid: str) -> dict:
    """Load locally cached credentials for a specified UID; returns None if missing/expired."""
    if not uid:
        return None

    cache = _read_cache_file()
    entry = cache.get('credentials', {}).get(str(uid))
    if not entry or not _is_credential_valid(entry):
        return None

    return {
        'success': True,
        'access_key_id': entry.get('access_key_id'),
        'access_key_secret': entry.get('access_key_secret'),
        'security_token': entry.get('security_token'),
        'expiration': entry.get('expiration'),
        'from_cache': True,
    }


def save_credentials_to_cache(uid: str, result: dict):
    """
    Write credentials to local cache. Multi-UID coexistence:
    - Overwrite/add entry for current UID, keep other UIDs unchanged
    - Also clean up expired entries for other UIDs
    """
    if not result.get('success') or not uid:
        return

    cache = _read_cache_file()
    credentials = cache.get('credentials', {}) or {}

    credentials = {
        k: v for k, v in credentials.items()
        if k == str(uid) or _is_credential_valid(v)
    }

    credentials[str(uid)] = {
        'access_key_id': result.get('access_key_id'),
        'access_key_secret': result.get('access_key_secret'),
        'security_token': result.get('security_token'),
        'expiration': result.get('expiration'),
        'cached_at': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    payload = {'last_active_uid': str(uid), 'credentials': credentials}
    try:
        with open(STS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.chmod(STS_CACHE_FILE, 0o600)  # restrict credential cache to owner read/write only
    except OSError as e:
        print(f"Warning: Cache write failed: {e}", file=sys.stderr)


# ---------------- Credential Retrieval ----------------

def get_credentials_via_default_chain(region_id: str = "cn-hangzhou") -> dict:
    """Validate credentials via SDK default credential chain.

    The SDK resolves credentials automatically from environment variables,
    credentials file, CLI config, or instance metadata. This function simply
    verifies the chain works by calling GetCallerIdentity.
    """
    try:
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkcore.request import CommonRequest
        from aliyunsdkcore.auth.credentials import StsTokenCredential
    except ImportError:
        return {
            "success": False,
            "error_code": "SDKNotInstalled",
            "error_message": "aliyunsdkcore not installed. Run: pip install aliyun-python-sdk-core",
        }

    # Silence benign "Exception ignored in AcsClient.__del__" noise the SDK emits
    # when a client fails to initialize (partial object lacks a 'session' attribute).
    _orig_acs_del = getattr(AcsClient, "__del__", None)
    if _orig_acs_del is not None and not getattr(_orig_acs_del, "_quiet", False):
        def _quiet_acs_del(self, _orig=_orig_acs_del):
            try:
                _orig(self)
            except Exception:
                pass
        _quiet_acs_del._quiet = True
        AcsClient.__del__ = _quiet_acs_del

    try:
        ak = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
        sk = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        token = os.environ.get("ALIBABA_CLOUD_SECURITY_TOKEN")
        if ak and sk:
            if token:
                # AcsClient has no set_security_token method; STS tokens must be
                # injected via a StsTokenCredential (aliyun-python-sdk-core).
                client = AcsClient(region_id=region_id,
                                   credential=StsTokenCredential(ak, sk, token))
            else:
                client = AcsClient(ak, sk, region_id)
        else:
            client = AcsClient(region_id=region_id)
        req = CommonRequest()
        req.set_accept_format("json")
        req.set_domain("sts.aliyuncs.com")
        req.set_method("POST")
        req.set_protocol_type("https")
        req.set_version("2015-04-01")
        req.set_action_name("GetCallerIdentity")
        resp = json.loads(client.do_action_with_exception(req))
        return {
            "success": True,
            "uid": resp.get("AccountId", ""),
            "arn": resp.get("Arn", ""),
            "credential_chain": "sdk_default",
            "expiration": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error_code": "DefaultChainFailed",
            "error_message": f"SDK default credential chain validation failed: {e}\n"
                             "Please ensure credentials are configured via one of:\n"
                             "  - Environment variables (ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET)\n"
                             "  - Credentials file (~/.alibabacloud/credentials)\n"
                             "  - Aliyun CLI config (aliyun configure)\n"
                             "  - ECS instance RAM role",
        }


def get_credentials_from_cli(profile: str = "default") -> dict:
    """Get credentials from aliyun CLI configuration (compatible with v2 and v3).

    aliyun CLI v3.0 removed the `configure get --field` command,
    now reads ~/.aliyun/config.json directly.
    """
    config_path = Path.home() / ".aliyun" / "config.json"
    if not config_path.exists():
        return {
            "success": False,
            "error_code": "AliyunCLINotFound",
            "error_message": "Aliyun CLI config file not found. Please install aliyun CLI and run: aliyun configure\n"
                             "  macOS: brew install aliyun-cli\n"
                             "  Other: https://github.com/aliyun/aliyun-cli/releases",
        }

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {
            "success": False,
            "error_code": "CLIConfigError",
            "error_message": f"Aliyun CLI config file read failed: {e}\nPlease run: aliyun configure",
        }

    # Find specified profile
    profiles = config.get("profiles", [])
    target = None
    for p in profiles:
        if p.get("name") == profile:
            target = p
            break

    if not target:
        return {
            "success": False,
            "error_code": "CLINoCredentials",
            "error_message": f"Profile '{profile}' not found in aliyun CLI config. Please run: aliyun configure",
        }

    ak = target.get("access_key_id", "")
    sk = target.get("access_key_secret", "")
    token = target.get("sts_token", "") or target.get("security_token", "")

    if not ak or not sk:
        return {
            "success": False,
            "error_code": "CLINoCredentials",
            "error_message": "No valid credentials found in aliyun CLI config. Please run: aliyun configure",
        }

    return {
        "success": True,
        "access_key_id": ak,
        "access_key_secret": sk,
        "security_token": token if token else None,
        "expiration": None,
    }


def verify_caller_identity(ak: str, sk: str, token: str = None,
                           region_id: str = "cn-hangzhou") -> dict:
    """Confirm credentials by calling STS GetCallerIdentity.

    Loading keys from the aliyun CLI config (or AssumeRole) does not by itself
    prove the credentials are usable. This calls GetCallerIdentity to validate
    them and surface the AccountId / Arn identity fields.
    """
    try:
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkcore.request import CommonRequest
        from aliyunsdkcore.auth.credentials import StsTokenCredential
    except ImportError:
        return {"success": False, "error_code": "SDKNotInstalled",
                "error_message": "aliyunsdkcore not installed. Run: pip install aliyun-python-sdk-core"}

    # Silence benign AcsClient.__del__ noise on partial init failures.
    _orig_acs_del = getattr(AcsClient, "__del__", None)
    if _orig_acs_del is not None and not getattr(_orig_acs_del, "_quiet", False):
        def _quiet_acs_del(self, _orig=_orig_acs_del):
            try:
                _orig(self)
            except Exception:
                pass
        _quiet_acs_del._quiet = True
        AcsClient.__del__ = _quiet_acs_del

    try:
        if token:
            client = AcsClient(region_id=region_id,
                               credential=StsTokenCredential(ak, sk, token))
        else:
            client = AcsClient(ak, sk, region_id)
        req = CommonRequest()
        req.set_accept_format("json")
        req.set_domain("sts.aliyuncs.com")
        req.set_method("POST")
        req.set_protocol_type("https")
        req.set_version("2015-04-01")
        req.set_action_name("GetCallerIdentity")
        resp = json.loads(client.do_action_with_exception(req))
        return {"success": True,
                "account_id": resp.get("AccountId", ""),
                "arn": resp.get("Arn", ""),
                "user_id": resp.get("UserId", "")}
    except Exception as e:
        return {"success": False, "error_code": "GetCallerIdentityFailed",
                "error_message": f"GetCallerIdentity failed: {e}"}


def get_credentials_via_assume_role(role_arn: str, session_name: str = "ecs-vpc-check",
                                    duration: int = 3600) -> dict:
    """Get temporary credentials via STS AssumeRole.

    Security: all arguments are strictly validated before being passed to the
    subprocess, which is invoked as an argument list (never via a shell) to
    prevent command/argument injection from crafted parameters.
    """
    if not re.match(r'^acs:ram::\d+:role/[A-Za-z0-9+=,.@_-]+$', role_arn or ""):
        return {"success": False, "error_code": "InvalidRoleArn",
                "error_message": "role_arn must match acs:ram::<uid>:role/<name>"}
    if not re.match(r'^[A-Za-z0-9.@_-]{1,64}$', session_name or ""):
        return {"success": False, "error_code": "InvalidSessionName",
                "error_message": "session_name contains invalid characters"}
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        return {"success": False, "error_code": "InvalidDuration",
                "error_message": "duration must be an integer"}
    if not (900 <= duration <= 43200):
        return {"success": False, "error_code": "InvalidDuration",
                "error_message": "duration must be between 900 and 43200 seconds"}
    try:
        cmd = [
            "aliyun", "sts", "AssumeRole",
            "--RoleArn", role_arn,
            "--RoleSessionName", session_name,
            "--DurationSeconds", str(duration),
        ]
        output = subprocess.check_output(cmd, stderr=subprocess.PIPE, text=True)
        data = json.loads(output)

        creds = data.get("Credentials", {})
        ak = creds.get("AccessKeyId")
        sk = creds.get("AccessKeySecret")
        token = creds.get("SecurityToken")
        exp = creds.get("Expiration")

        if not (ak and sk and token):
            return {
                "success": False,
                "error_code": "InvalidAssumeRoleResponse",
                "error_message": f"AssumeRole response missing required fields: {output[:200]}",
            }

        return {
            "success": True,
            "access_key_id": ak,
            "access_key_secret": sk,
            "security_token": token,
            "expiration": exp,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error_code": "AliyunCLINotFound",
            "error_message": "Aliyun CLI not found. Please install and configure credentials.",
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error_code": "AssumeRoleFailed",
            "error_message": f"AssumeRole call failed: {e.stderr.strip() if e.stderr else e}",
        }


# ---------------- Output ----------------

def _mask_secret(value: str, keep_prefix: int = 4, keep_suffix: int = 2) -> str:
    """Mask a sensitive credential value, keeping only a short prefix/suffix.

    Prevents AccessKey ID / Secret / STS token from being exposed in plaintext
    in stdout or execution logs. The full credentials are still written to the
    local cache file (.sts_cache.json) for business scripts to read.
    """
    if not value:
        return ""
    value = str(value)
    if len(value) <= keep_prefix + keep_suffix:
        return "*" * len(value)
    return f"{value[:keep_prefix]}{'*' * 8}{value[-keep_suffix:]}"


def print_result(result: dict, format_json: bool = False):
    if format_json:
        # Mask sensitive fields before printing; full credentials live in cache file.
        safe = dict(result)
        for _k in ("access_key_id", "access_key_secret", "security_token"):
            if safe.get(_k):
                safe[_k] = _mask_secret(safe[_k])
        print(json.dumps(safe, indent=2, ensure_ascii=False))
        return

    if not result.get("success"):
        print("\n" + "=" * 60)
        print("Failed to obtain Alibaba Cloud credentials")
        print("=" * 60)
        print(f"\nError Code: {result.get('error_code')}")
        print(f"Error Message: {result.get('error_message')}")
        print("\n" + "=" * 60)
        return

    print("\n" + "=" * 60)
    print("Alibaba Cloud credentials obtained successfully")
    print("=" * 60)
    account_id = result.get('account_id') or result.get('uid')
    arn = result.get('arn')
    if account_id or arn:
        print(f"\n[Identity]")
        if account_id:
            print(f"  AccountId: {account_id}")
        if arn:
            print(f"  Arn:       {arn}")
    print(f"\n[Credentials]")
    print(f"  AccessKey ID:     {_mask_secret(result.get('access_key_id'))}")
    print(f"  AccessKey Secret: {_mask_secret(result.get('access_key_secret'))}")
    if result.get('security_token'):
        print(f"  Security Token:   {_mask_secret(result.get('security_token'))}")
    if result.get('expiration'):
        print(f"\n[Expiration]")
        print(f"  {result.get('expiration')}")
    print("\n" + "=" * 60)
    print("Credentials written to local cache (scripts/.sts_cache.json), business scripts will auto-read.")
    if result.get('from_cache'):
        remaining = ""
        expiration = result.get('expiration', '')
        if expiration:
            try:
                exp_str = expiration.replace('Z', '+00:00')[:19]
                exp_time = datetime.strptime(exp_str, "%Y-%m-%dT%H:%M:%S")
                delta = exp_time - datetime.utcnow()
                mins = int(delta.total_seconds() // 60)
                remaining = f"(approximately {mins} minutes remaining)"
            except Exception:
                pass
        print(f"Credential source: local cache {remaining}")
    print("\n" + "=" * 60)


# ---------------- Entry Point ----------------

def main():
    parser = argparse.ArgumentParser(
        description="Get Alibaba Cloud access credentials (for customer self-service use)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate SDK default credential chain
  python sts_create.py

  # Get from aliyun CLI configuration
  python sts_create.py --cli

  # Get STS temporary credentials via AssumeRole
  python sts_create.py --role-arn acs:ram::<UID>:role/<ROLE_NAME>

  # JSON output
  python sts_create.py --cli --json
        """,
    )
    parser.add_argument("--uid", help="User UID (optional, used for cache indexing)")
    parser.add_argument("--cli", action="store_true",
                        help="Get credentials from aliyun CLI configuration")
    parser.add_argument("--role-arn",
                        help="Get STS temporary credentials via AssumeRole (specify role ARN)")
    parser.add_argument("--profile", default="default",
                        help="aliyun CLI profile name (default: default)")
    parser.add_argument("--force-refresh", action="store_true",
                        help="Force refresh credentials, ignore local cache")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    args = parser.parse_args()

    uid = str(args.uid).strip() if args.uid else "default"

    # Hit local cache
    if not args.force_refresh:
        cached = load_cached_credentials(uid)
        if cached:
            _update_last_active_uid(uid)
            print_result(cached, format_json=args.json)
            sys.exit(0)

    # Get credentials by priority
    if args.role_arn:
        result = get_credentials_via_assume_role(args.role_arn)
    elif args.cli:
        result = get_credentials_from_cli(profile=args.profile)
    else:
        result = get_credentials_via_default_chain()
        # The SDK default chain does not read the aliyun CLI config
        # (~/.aliyun/config.json); fall back to it so a bare invocation still
        # works when credentials are provisioned via `aliyun configure`.
        if not result.get("success"):
            cli_result = get_credentials_from_cli(profile=args.profile)
            if cli_result.get("success"):
                result = cli_result

    # For key-only sources (CLI config / AssumeRole), confirm the credentials
    # via GetCallerIdentity so identity (AccountId/Arn) is verified and shown.
    if result.get("success") and result.get("access_key_id") and not result.get("account_id"):
        identity = verify_caller_identity(
            result.get("access_key_id"),
            result.get("access_key_secret"),
            result.get("security_token"),
        )
        if identity.get("success"):
            result["account_id"] = identity.get("account_id")
            result["arn"] = identity.get("arn")
            result["user_id"] = identity.get("user_id")

    print_result(result, format_json=args.json)

    if result.get('success'):
        save_credentials_to_cache(uid, result)

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
