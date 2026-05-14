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
    """Auto-install the ModelStudio plugin."""
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
            print("✓ ModelStudio plugin installed successfully", file=sys.stderr)
            return True
        print(f"⚠️  ModelStudio plugin installation failed: {result.stderr.strip()}", file=sys.stderr)
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_aliyun_cli() -> bool:
    """Check if Alibaba Cloud CLI and ModelStudio plugin are available. Auto-installs plugin if missing."""
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
    # Plugin not installed, attempt auto-install
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
        RuntimeError: When unable to retrieve
    """
    try:
        result = subprocess.run(
            ["aliyun", "modelstudio", "list-workspaces",
             "--region", "cn-beijing",
             "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-bailian-video-creator"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_API
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Get Workspace timed out ({TIMEOUT_API}s), please check network connection")

    if result.returncode != 0:
        raise RuntimeError(f"Failed to get Workspace: {result.stderr.strip()}")

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
        raise RuntimeError(f"Failed to parse Workspace response: {result.stdout}")


def generate_api_key(description: str = "AI Agent auto-generated, for bailian-video-creator") -> tuple[str, str]:
    """
    Create a real Bailian DashScope API Key via Alibaba Cloud CLI (ModelStudio plugin).

    Args:
        description: API Key description

    Returns:
        tuple[str, str]: (api_key_value, api_key_id)

    Raises:
        RuntimeError: When creation fails
    """
    if not check_aliyun_cli():
        raise RuntimeError(
            "Alibaba Cloud CLI or ModelStudio plugin not installed, cannot create API Key\n\n"
            "Please install first:\n"
            "  brew install aliyun-cli\n"
            "  aliyun plugin install --names aliyun-cli-modelstudio --enable-pre\n"
            "  aliyun configure\n\n"
            "Or manually obtain API Key: https://bailian.console.aliyun.com/cn-beijing/?tab=app#/api-key"
        )

    # Get workspace ID first
    workspace_id = _get_workspace_id()

    try:
        result = subprocess.run(
            ["aliyun", "modelstudio", "create-api-key",
             "--region", "cn-beijing",
             "--workspace-id", workspace_id,
             "--description", description,
             "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-bailian-video-creator"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_API
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Create API Key timed out ({TIMEOUT_API}s), please check network connection")
    except FileNotFoundError:
        raise RuntimeError("Alibaba Cloud CLI not installed")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "is not a valid" in stderr or "not found" in stderr.lower():
            raise RuntimeError(
                "API call failed, ModelStudio plugin may not be installed\n\n"
                "Please install the plugin:\n"
                "  aliyun plugin install --names aliyun-cli-modelstudio --enable-pre"
            )
        if "Forbidden" in stderr or "403" in stderr:
            raise RuntimeError(
                "Insufficient permissions, please check Alibaba Cloud CLI credential configuration\n\n"
                "  aliyun configure list    # View current configuration\n"
                "  aliyun configure         # Reconfigure"
            )
        if "超限" in stderr or "Quota" in stderr.lower() or "limit" in stderr.lower():
            raise RuntimeError(
                "API Key quota exceeded, cannot auto-create new Key\n\n"
                "Please resolve via one of the following:\n"
                "  1. Manually configure an existing API Key: export DASHSCOPE_API_KEY=sk-xxx\n"
                "  2. Delete unused Keys in the Bailian console and retry:\n"
                "     https://bailian.console.aliyun.com/cn-beijing/?tab=app#/api-key\n"
                "  3. Or run delete_api_key() to delete the Key created by this skill and retry"
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
    Save API Key to ~/.aliyun/config.json under the current profile.

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
            "Alibaba Cloud CLI configuration not found. Please run aliyun configure first"
        )

    dashscope = profile.setdefault("dashscope", {})
    dashscope["api_key"] = api_key
    if api_key_id:
        dashscope["api_key_id"] = api_key_id
    _write_aliyun_config(config)


def get_api_key() -> str:
    """
    Get DashScope API Key.

    Priority:
    1. Alibaba Cloud CLI config ~/.aliyun/config.json current profile's dashscope.api_key
    2. Environment variable DASHSCOPE_API_KEY
    3. Auto-create via Alibaba Cloud CLI and save

    Returns:
        str: API Key

    Raises:
        ValueError: When unable to obtain a valid API Key
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
            print(f"⚠️  Failed to read Alibaba Cloud CLI config: {e}", file=sys.stderr)

    # Priority 2: Environment variable
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if api_key:
        return _validate_api_key(api_key, "environment variable")

    # Priority 3: Auto-create via Alibaba Cloud CLI
    if check_aliyun_cli():
        print("No existing API Key found, auto-creating via Alibaba Cloud CLI...", file=sys.stderr)
        try:
            api_key_value, api_key_id = generate_api_key()
            save_api_key_to_config(api_key_value, api_key_id=api_key_id)
            print("✓ API Key auto-created and saved to Alibaba Cloud CLI config", file=sys.stderr)
            return _validate_api_key(api_key_value, "auto-created")
        except RuntimeError as e:
            print(f"⚠️  Auto-create API Key failed: {e}", file=sys.stderr)

    # All failed, raise error
    raise ValueError(
        "❌ No valid DASHSCOPE_API_KEY found\n\n"
        "Please configure via one of the following methods:\n"
        "  1. Manually set environment variable: export DASHSCOPE_API_KEY=sk-xxx\n"
        "  2. Write to ~/.aliyun/config.json current profile's dashscope.api_key\n"
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
            "value_preview": f"{api_key[:6]}...{api_key[-3:]}",
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
             "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-bailian-video-creator"],
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
    Delete the API Key in the current profile (both cloud and local).

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

        # 1. Attempt cloud deletion
        if api_key_id:
            cloud_result = _delete_cloud_api_key(api_key_id)
            if cloud_result["success"]:
                messages.append(cloud_result["message"])
            else:
                messages.append(f"⚠️  {cloud_result['error']} (continuing with local deletion)")
        else:
            messages.append("No cloud API Key ID found, skipping cloud deletion")

        # 2. Delete local record
        profile.pop("dashscope", None)
        _write_aliyun_config(config)
        messages.append(f"Local record deleted from profile '{profile_name}'")

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
        ValueError: When Key format is incorrect
    """
    # Check if it's a Coding Plan Key
    if api_key.startswith("sk-sp-"):
        raise ValueError(
            f"❌ Got a DashScope Coding Plan API Key (sk-sp-xxx) from {source}\n\n"
            "⚠️  DASHSCOPE_API_KEY and DashScope Coding Plan API Key are two different keys!\n"
            "   - Current Key (sk-sp-xxx) is only for the Coding Plan service, does not support video generation\n"
            "   - Video generation requires a standard DASHSCOPE_API_KEY (sk-xxx)\n\n"
            "Please configure the correct environment variable:\n"
            "  export DASHSCOPE_API_KEY=sk-xxx\n\n"
            "Obtain API Key: https://help.aliyun.com/zh/model-studio/get-api-key"
        )

    # Check format
    if not api_key.startswith("sk-"):
        raise ValueError(
            f"❌ API Key from {source} has incorrect format: {api_key[:10]}...\n\n"
            "A standard DASHSCOPE_API_KEY should start with 'sk-'\n"
            "Please check your configuration"
        )

    print(f"✓ Got API Key from {source}: {api_key[:6]}...{api_key[-3:]}", file=sys.stderr)
    return api_key
