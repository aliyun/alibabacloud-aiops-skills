#!/usr/bin/env python3
"""
Bailian DashScope API Key Management Module
Handles API Key creation, storage, retrieval, deletion, and format validation.

Storage location: ~/.aliyun/config.json (Alibaba Cloud CLI config file)
Storage method: Adds a dashscope field (sub-object) to the current profile
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
ALIYUN_CONFIG_DIR = Path.home() / ".aliyun"
ALIYUN_CONFIG_FILE = ALIYUN_CONFIG_DIR / "config.json"
TIMEOUT_API = 30  # API call timeout (seconds)


def _read_aliyun_config() -> dict:
    """Read the Alibaba Cloud CLI config file."""
    if not ALIYUN_CONFIG_FILE.exists():
        return {}
    with open(ALIYUN_CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _write_aliyun_config(config: dict) -> None:
    """Write to the Alibaba Cloud CLI config file."""
    ALIYUN_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(ALIYUN_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent='\t')
    ALIYUN_CONFIG_FILE.chmod(0o600)


def _get_current_profile(config: dict) -> dict | None:
    """Get the currently active profile."""
    current = config.get("current", "default")
    for profile in config.get("profiles", []):
        if profile.get("name") == current:
            return profile
    return None


def _check_aliyun_binary() -> bool:
    """Check if Alibaba Cloud CLI binary is installed."""
    try:
        result = subprocess.run(
            ["aliyun", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _install_modelstudio_plugin() -> bool:
    """Auto-install ModelStudio plugin if missing."""
    try:
        print("Auto-installing ModelStudio plugin...", file=sys.stderr)
        result = subprocess.run(
            ["aliyun", "plugin", "install",
             "--names", "aliyun-cli-modelstudio", "--enable-pre"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print("ModelStudio plugin installed successfully", file=sys.stderr)
            return True
        print(f"Warning: ModelStudio plugin installation failed: {result.stderr.strip()}", file=sys.stderr)
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_aliyun_cli() -> bool:
    """Check if Alibaba Cloud CLI and ModelStudio plugin are available, auto-install plugin if missing."""
    if not _check_aliyun_binary():
        return False
    # Check ModelStudio plugin
    try:
        result = subprocess.run(
            ["aliyun", "modelstudio", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    # Plugin not installed, try auto-install
    if not _install_modelstudio_plugin():
        return False
    # Verify after installation
    try:
        result = subprocess.run(
            ["aliyun", "modelstudio", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _get_workspace_id() -> str:
    """
    Get the default Bailian workspace ID.

    Returns:
        str: workspace ID

    Raises:
        RuntimeError: When unable to retrieve the workspace ID
    """
    try:
        result = subprocess.run(
            ["aliyun", "modelstudio", "list-workspaces",
             "--region", "cn-beijing",
             "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-bailian-image-creator"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_API
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Workspace retrieval timed out ({TIMEOUT_API}s). Please check your network connection")

    if result.returncode != 0:
        raise RuntimeError(f"Failed to retrieve workspace: {result.stderr.strip()}")

    try:
        data = json.loads(result.stdout)
        workspaces = data.get("workspaces", [])
        if not workspaces:
            raise RuntimeError(
                "No Bailian Workspace found. Please create one in the console first:\n"
                "  https://bailian.console.aliyun.com/"
            )
        return workspaces[0]["workspaceId"]
    except (json.JSONDecodeError, KeyError, IndexError):
        raise RuntimeError(f"Failed to parse workspace response: {result.stdout}")


def _list_cloud_api_keys(workspace_id: str) -> list:
    """
    List existing cloud API Keys via Alibaba Cloud CLI.

    Args:
        workspace_id: Bailian Workspace ID

    Returns:
        list: API Key list (each item contains apiKeyId, description, etc.)
    """
    try:
        result = subprocess.run(
            ["aliyun", "modelstudio", "list-api-keys",
             "--region", "cn-beijing",
             "--workspace-id", workspace_id,
             "--page-size", "100",
             "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-bailian-image-creator"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_API
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if result.returncode != 0:
        return []

    try:
        data = json.loads(result.stdout)
        return data.get("apiKeys", [])
    except (json.JSONDecodeError, KeyError):
        return []


def generate_api_key(
    description: str = "AI Agent auto-generated, for bailian-image-creator",
    _retry: bool = False,
) -> tuple[str, str]:
    """
    Create a real Bailian DashScope API Key via Alibaba Cloud CLI (ModelStudio plugin).

    When hitting the API Key count limit, automatically cleans up old auto-generated keys
    and retries once.

    Args:
        description: API Key description
        _retry: Internal flag to prevent infinite recursion

    Returns:
        tuple[str, str]: (api_key_value, api_key_id)

    Raises:
        RuntimeError: When creation fails
    """
    if not check_aliyun_cli():
        raise RuntimeError(
            "Alibaba Cloud CLI or ModelStudio plugin is not installed. Cannot create API Key\n\n"
            "Please install first:\n"
            "  brew install aliyun-cli\n"
            "  aliyun plugin install --names aliyun-cli-modelstudio --enable-pre\n"
            "  aliyun configure\n\n"
            "Or manually obtain an API Key: https://bailian.console.aliyun.com/cn-beijing/?tab=app#/api-key"
        )

    # Get workspace ID first
    workspace_id = _get_workspace_id()

    # Idempotent check-then-act: clean up orphan keys from failed previous attempts.
    # When generate_api_key() is called, it means no key is saved locally. If a cloud
    # key with our description already exists, it's an orphan from a timed-out previous
    # call (created on cloud but never saved locally). Delete orphans first to avoid
    # accumulating duplicate keys on retry.
    if not _retry:
        existing_keys = _list_cloud_api_keys(workspace_id)
        orphans = [k for k in existing_keys
                   if description in k.get("description", "")]
        for orphan in orphans:
            orphan_id = str(orphan.get("apiKeyId", ""))
            if orphan_id:
                print(f"  Cleaning up orphan key from previous attempt: ID={orphan_id}", file=sys.stderr)
                _delete_cloud_api_key(orphan_id)

    try:
        result = subprocess.run(
            ["aliyun", "modelstudio", "create-api-key",
             "--region", "cn-beijing",
             "--workspace-id", workspace_id,
             "--description", description,
             "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-bailian-image-creator"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_API
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"API Key creation timed out ({TIMEOUT_API}s). Please check your network connection")
    except FileNotFoundError:
        raise RuntimeError("Alibaba Cloud CLI is not installed")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "is not a valid" in stderr or "not found" in stderr.lower():
            raise RuntimeError(
                "API call failed. The ModelStudio plugin may not be installed\n\n"
                "Please install the plugin:\n"
                "  aliyun plugin install --names aliyun-cli-modelstudio --enable-pre"
            )
        if "Forbidden" in stderr or "403" in stderr:
            raise RuntimeError(
                "Insufficient permissions. Please check your Alibaba Cloud CLI credentials\n\n"
                "  aliyun configure list    # View current configuration\n"
                "  aliyun configure         # Reconfigure"
            )
        # Handle API Key count limit: only recycle keys created by this skill, never delete others
        if not _retry and ("Limit" in stderr or "limit" in stderr.lower()):
            print("Warning: API Key count has reached the limit. Attempting to recycle old keys from this skill...", file=sys.stderr)
            existing_keys = _list_cloud_api_keys(workspace_id)
            # Only recycle keys created by this skill (matched by description), never touch other keys
            recyclable = [k for k in existing_keys
                          if description in k.get("description", "")]
            if recyclable:
                old_key_id = str(recyclable[0].get("apiKeyId", ""))
                old_key_desc = recyclable[0].get("description", "")
                if old_key_id:
                    print(f"  Found recyclable old key: ID={old_key_id}, description='{old_key_desc}'", file=sys.stderr)
                    delete_result = _delete_cloud_api_key(old_key_id)
                    if delete_result["success"]:
                        print(f"Old key recycled (ID: {old_key_id}). Recreating...", file=sys.stderr)
                        return generate_api_key(description, _retry=True)
            raise RuntimeError(
                "API Key count has reached account limit and no recyclable keys from this skill were found\n\n"
                "Please manually delete unused API Keys:\n"
                "  https://bailian.console.aliyun.com/cn-beijing/?tab=app#/api-key"
            )
        raise RuntimeError(f"Failed to create API Key: {stderr}")

    try:
        data = json.loads(result.stdout)
        api_key_info = data.get("apiKey", {})
        api_key_value = api_key_info.get("apiKeyValue")
        api_key_id = str(api_key_info.get("apiKeyId", ""))
        if not api_key_value:
            raise RuntimeError(f"API response missing apiKeyValue: {result.stdout}")
        return api_key_value, api_key_id
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse API response: {result.stdout}")


def save_api_key_to_config(api_key: str, description: str = "", api_key_id: str = "") -> None:
    """
    Save API Key to the current profile in ~/.aliyun/config.json.

    Args:
        api_key: API Key string
        description: API Key description (unused, kept for interface compatibility)
        api_key_id: Cloud API Key ID (used for subsequent cloud deletion)
    """
    try:
        config = _read_aliyun_config()
    except Exception:
        config = {}

    profile = _get_current_profile(config)
    if profile is None:
        raise RuntimeError(
            "Alibaba Cloud CLI config not found. Please run 'aliyun configure' to complete initial setup"
        )

    dashscope = profile.setdefault("dashscope", {})
    dashscope["api_key"] = api_key
    if api_key_id:
        dashscope["api_key_id"] = api_key_id
    _write_aliyun_config(config)


def get_api_key() -> str:
    """
    Retrieve the DashScope API Key.

    Priority:
    1. Alibaba Cloud CLI config ~/.aliyun/config.json current profile's dashscope.api_key
    2. Environment variable DASHSCOPE_API_KEY
    3. Auto-create via Alibaba Cloud CLI and save to config

    Returns:
        str: API Key

    Raises:
        ValueError: When no valid API Key can be found
    """
    # Priority 1: Alibaba Cloud CLI config file
    if ALIYUN_CONFIG_FILE.exists():
        try:
            config = _read_aliyun_config()
            profile = _get_current_profile(config)
            if profile:
                dashscope = profile.get("dashscope", {})
                api_key = dashscope.get("api_key")
                if api_key:
                    return _validate_api_key(api_key, f"Alibaba Cloud CLI config ({ALIYUN_CONFIG_FILE})")
        except Exception as e:
            print(f"Warning: Failed to read Alibaba Cloud CLI config: {e}", file=sys.stderr)

    # Priority 2: Environment variable
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if api_key:
        return _validate_api_key(api_key, "environment variable")

    # Priority 3: Auto-create via Alibaba Cloud CLI
    if check_aliyun_cli():
        print("No existing API Key found. Auto-creating via Alibaba Cloud CLI...", file=sys.stderr)
        try:
            api_key_value, api_key_id = generate_api_key()
            save_api_key_to_config(api_key_value, api_key_id=api_key_id)
            print("API Key auto-created and saved to Alibaba Cloud CLI config", file=sys.stderr)
            return _validate_api_key(api_key_value, "auto-created")
        except RuntimeError as e:
            print(f"Warning: Failed to auto-create API Key: {e}", file=sys.stderr)

    # All methods failed
    raise ValueError(
        "No valid DASHSCOPE_API_KEY found\n\n"
        "Please configure using one of the following methods:\n"
        "  1. Set environment variable: export DASHSCOPE_API_KEY=sk-xxx\n"
        "  2. Write to dashscope.api_key in current profile of ~/.aliyun/config.json\n"
        "  3. Install Alibaba Cloud CLI for auto-creation:\n"
        "     brew install aliyun-cli\n"
        "     aliyun plugin install --names aliyun-cli-modelstudio --enable-pre\n"
        "     aliyun configure\n\n"
        "Obtain API Key: https://bailian.console.aliyun.com/cn-beijing/?tab=app#/api-key"
    )


def list_saved_keys() -> dict:
    """
    List saved API Keys.

    Returns:
        dict: Dictionary containing saved API Key information
    """
    if not ALIYUN_CONFIG_FILE.exists():
        return {
            "success": True,
            "message": "Alibaba Cloud CLI config file not found",
            "keys": []
        }

    try:
        config = _read_aliyun_config()
        profile = _get_current_profile(config)
        if not profile:
            return {"success": True, "message": "Current profile not found", "keys": []}

        dashscope = profile.get("dashscope", {})
        api_key = dashscope.get("api_key")
        if not api_key:
            return {"success": True, "message": "No dashscope api_key in current profile", "keys": []}

        key_info = {
            "profile": profile.get("name", "unknown"),
            "value_preview": f"{api_key[:3]}***",
        }
        api_key_id = dashscope.get("api_key_id")
        if api_key_id:
            key_info["api_key_id"] = api_key_id

        return {
            "success": True,
            "keys": [key_info]
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read config file: {e}"
        }


def _delete_cloud_api_key(api_key_id: str) -> dict:
    """
    Delete a cloud API Key via Alibaba Cloud CLI.

    Args:
        api_key_id: Cloud API Key ID (numeric)

    Returns:
        dict: Operation result
    """
    if not check_aliyun_cli():
        return {
            "success": False,
            "error": "Alibaba Cloud CLI or ModelStudio plugin not installed, skipping cloud deletion"
        }

    try:
        result = subprocess.run(
            ["aliyun", "modelstudio", "delete-api-key",
             "--region", "cn-beijing",
             "--api-key-id", api_key_id,
             "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-bailian-image-creator"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_API
        )
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Cloud deletion timed out ({TIMEOUT_API}s)"}

    if result.returncode != 0:
        stderr = result.stderr.strip()
        return {"success": False, "error": f"Cloud deletion failed: {stderr}"}

    return {"success": True, "message": f"Cloud API Key (ID: {api_key_id}) deleted"}


def delete_api_key() -> dict:
    """
    Delete the API Key in the current profile (with protective pre-checks).

    Pre-check rules:
    - No api_key_id (manually configured key): only remove local ref, skip cloud deletion
    - Has api_key_id: query cloud to confirm ownership by this skill before cloud deletion

    Returns:
        dict: Operation result
    """
    if not ALIYUN_CONFIG_FILE.exists():
        return {
            "success": False,
            "error": "Alibaba Cloud CLI config file does not exist"
        }

    try:
        config = _read_aliyun_config()
        profile = _get_current_profile(config)
        if not profile:
            return {"success": False, "error": "Current profile not found"}

        dashscope = profile.get("dashscope", {})
        api_key = dashscope.get("api_key")
        if not api_key:
            return {"success": False, "error": "No dashscope api_key in current profile"}

        profile_name = profile.get("name", "unknown")
        api_key_id = dashscope.get("api_key_id")
        messages = []

        # Protective pre-check: only delete cloud keys auto-created by this skill
        if api_key_id:
            # Has api_key_id, possibly auto-created; verify cloud description to confirm
            skill_description = "bailian-image-creator"
            should_delete_cloud = False
            try:
                workspace_id = _get_workspace_id()
                existing_keys = _list_cloud_api_keys(workspace_id)
                matched = [k for k in existing_keys
                           if str(k.get("apiKeyId", "")) == str(api_key_id)]
                if matched:
                    desc = matched[0].get("description", "")
                    if skill_description in desc:
                        should_delete_cloud = True
                    else:
                        print(f"Warning: Cloud key (ID={api_key_id}) description '{desc}' "
                              f"does not match skill identifier '{skill_description}', "
                              f"skipping cloud deletion",
                              file=sys.stderr)
                        messages.append("Cloud key description does not match this skill, "
                                        "skipping cloud deletion (safety)")
                else:
                    messages.append(f"Cloud key ID={api_key_id} not found, skipping cloud deletion")
            except RuntimeError as e:
                messages.append(f"Cannot query cloud key status: {e}, skipping cloud deletion")

            if should_delete_cloud:
                print(f"Confirmed cloud key (ID={api_key_id}) was auto-created by this skill, deleting...",
                      file=sys.stderr)
                cloud_result = _delete_cloud_api_key(api_key_id)
                if cloud_result["success"]:
                    messages.append(cloud_result["message"])
                else:
                    messages.append(f"Warning: {cloud_result['error']} (proceeding with local deletion)")
        else:
            # No api_key_id means manually configured key, possibly shared by other services
            print("Warning: Key has no api_key_id (likely manually configured), "
                  "only removing local reference, skipping cloud deletion",
                  file=sys.stderr)
            messages.append("Key is manually configured, only removing local reference, "
                            "cloud key not deleted")

        # Delete local record
        profile.pop("dashscope", None)
        _write_aliyun_config(config)
        messages.append(f"Local record removed from profile '{profile_name}'")

        return {
            "success": True,
            "message": "; ".join(messages)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Deletion failed: {e}"
        }


def _validate_api_key(api_key: str, source: str) -> str:
    """
    Validate API Key format.

    Args:
        api_key: API Key string
        source: Key source (used in error messages)

    Returns:
        str: Valid API Key

    Raises:
        ValueError: When the Key format is invalid
    """
    # Check if it's a Coding Plan Key
    if api_key.startswith("sk-sp-"):
        raise ValueError(
            f"Got a DashScope Coding Plan API Key (sk-sp-xxx) from {source}\n\n"
            "DASHSCOPE_API_KEY and DashScope Coding Plan API Key are two different keys!\n"
            "   - Current Key (sk-sp-xxx) is only for the Coding Plan service, does not support image generation\n"
            "   - Image generation requires a standard DASHSCOPE_API_KEY (sk-xxx)\n\n"
            "Please configure the correct environment variable:\n"
            "  export DASHSCOPE_API_KEY=sk-xxx\n\n"
            "Obtain API Key: https://help.aliyun.com/zh/model-studio/get-api-key"
        )

    # Check format
    if not api_key.startswith("sk-"):
        raise ValueError(
            f"API Key from {source} has invalid format: {api_key[:10]}...\n\n"
            "A standard DASHSCOPE_API_KEY should start with 'sk-'\n"
            "Please check your configuration"
        )

    print(f"API Key retrieved from {source}: {api_key[:3]}***", file=sys.stderr)
    return api_key
