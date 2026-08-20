#!/usr/bin/env python3
"""
SysOM alert strategy creation script

Purpose: create an alert strategy via the SDK (supports the destinations parameter, which the CLI does not)
Usage: SKILL_SESSION_ID=<session-id> .sysom-sdk-venv/bin/python scripts/create-alert-strategy.py \
        --name <strategy_name> \
        --items <alert_item_1>,<alert_item_2> \
        --clusters <cluster_1> \
        --destinations <destination_id_1>,<destination_id_2>

Arguments:
  --name          Strategy name (required)
  --items         Alert item names, comma-separated (required)
  --clusters      Clusters, comma-separated (required; use default for instance mode)
  --destinations  Alert destination IDs, comma-separated (required)
  --k8s-label     Enable k8s labels (optional, defaults to false)

Credential sources (in priority order):
  1. Environment variables ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
  2. aliyun CLI config file ~/.aliyun/config.json (current profile is read automatically)

Observability:
  The SDK User-Agent follows the skill UA template
  AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id},
  where {session-id} comes from the SKILL_SESSION_ID environment variable and MUST be the
  same value used by the aliyun CLI commands of the current session.

Returns:
  On success, prints the strategy name to stdout and details to stderr
"""

import argparse
import json
import os
import sys
import uuid

SKILL_NAME = "alibabacloud-aes-sysom-lingjun-diagnosis"
USER_AGENT_PREFIX = "AlibabaCloud-Agent-Skills"


def build_user_agent():
    session_id = os.environ.get("SKILL_SESSION_ID", "").strip()
    if not session_id:
        session_id = uuid.uuid4().hex
        print(
            "⚠️  SKILL_SESSION_ID is not set; generated a temporary session-id for the User-Agent. "
            "Pass SKILL_SESSION_ID=<session-id> so SDK calls share the session-id used by CLI commands.",
            file=sys.stderr,
        )
    return f"{USER_AGENT_PREFIX}/{SKILL_NAME}/{session_id}"


def parse_arguments():
    parser = argparse.ArgumentParser(description="Create a SysOM alert strategy")
    parser.add_argument("--name", required=True, help="Strategy name")
    parser.add_argument("--items", required=True, help="Alert item names, comma-separated")
    parser.add_argument("--clusters", required=True, help="Clusters, comma-separated (use default for instance mode)")
    parser.add_argument("--destinations", required=True, help="Alert destination IDs, comma-separated")
    parser.add_argument("--k8s-label", action="store_true", default=False, help="Enable k8s labels")
    return parser.parse_args()


def load_credentials_from_cli_config():
    config_path = os.path.join(os.path.expanduser("~"), ".aliyun", "config.json")
    if not os.path.exists(config_path):
        return None, None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        current_profile = config.get("current", "")
        profiles = config.get("profiles", [])

        target_profile = None
        for profile in profiles:
            if profile.get("name") == current_profile:
                target_profile = profile
                break

        if not target_profile and profiles:
            target_profile = profiles[0]

        if target_profile:
            access_key_id = target_profile.get("access_key_id", "")
            access_key_secret = target_profile.get("access_key_secret", "")
            if access_key_id and access_key_secret:
                profile_name = target_profile.get("name", "default")
                print(f"🔑 Loaded credentials from aliyun CLI config (profile: {profile_name})", file=sys.stderr)
                return access_key_id, access_key_secret
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    return None, None

def validate_credentials():
    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

    if access_key_id and access_key_secret:
        print("🔑 Loaded credentials from environment variables", file=sys.stderr)
        return access_key_id, access_key_secret

    access_key_id, access_key_secret = load_credentials_from_cli_config()
    if access_key_id and access_key_secret:
        return access_key_id, access_key_secret

    print("❌ No Alibaba Cloud credentials found. Configure them in one of the following ways:", file=sys.stderr)
    print("   Option 1: aliyun configure (recommended, read automatically by this script)", file=sys.stderr)
    print("   Option 2: export ALIBABA_CLOUD_ACCESS_KEY_ID=<your_ak>", file=sys.stderr)
    print("          export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your_sk>", file=sys.stderr)
    sys.exit(1)


def main():
    args = parse_arguments()
    access_key_id, access_key_secret = validate_credentials()

    items_list = [item.strip() for item in args.items.split(",") if item.strip()]
    clusters_list = [cluster.strip() for cluster in args.clusters.split(",") if cluster.strip()]

    try:
        destinations_list = [int(d.strip()) for d in args.destinations.split(",") if d.strip()]
    except ValueError:
        print("❌ Invalid --destinations format. Expected comma-separated integer IDs (e.g., 1,2,3)", file=sys.stderr)
        sys.exit(1)

    if not items_list:
        print("❌ At least one alert item is required (--items)", file=sys.stderr)
        sys.exit(1)

    if not destinations_list:
        print("❌ At least one alert destination ID is required (--destinations)", file=sys.stderr)
        sys.exit(1)

    try:
        from alibabacloud_tea_openapi.utils_models import Config
        from alibabacloud_sysom20231230.client import Client
        from alibabacloud_sysom20231230 import models
    except ImportError:
        print("❌ SDK is not installed. Run: bash scripts/setup-sdk.sh", file=sys.stderr)
        sys.exit(1)

    config = Config(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        endpoint="sysom.aliyuncs.com",
        user_agent=build_user_agent(),
        connect_timeout=10000,
        read_timeout=30000
    )
    client = Client(config)

    strategy = models.CreateAlertStrategyRequestStrategy(
        clusters=clusters_list,
        items=items_list,
        destinations=destinations_list
    )

    request = models.CreateAlertStrategyRequest(
        name=args.name,
        enabled=True,
        k_8s_label=args.k8s_label,
        strategy=strategy
    )

    try:
        response = client.create_alert_strategy(request)
        response_body = response.body

        if hasattr(response_body, "to_map"):
            result = response_body.to_map()
        else:
            result = {"body": str(response_body)}

        code = result.get("code", "")
        if code == "Success":
            print(args.name)
            print(f"✅ Alert strategy created successfully", file=sys.stderr)
            print(f"   Strategy name: {args.name}", file=sys.stderr)
            print(f"   Alert item count: {len(items_list)}", file=sys.stderr)
            print(f"   Clusters: {', '.join(clusters_list)}", file=sys.stderr)
            print(f"   Alert destination IDs: {destinations_list}", file=sys.stderr)
        else:
            message = result.get("message", "Unknown error")
            print(f"❌ Creation failed: {code} - {message}", file=sys.stderr)
            print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)

    except Exception as error:
        print(f"❌ API call failed: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
