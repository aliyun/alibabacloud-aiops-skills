#!/usr/bin/env python3
"""
Create Cluster VPC Endpoint Connection (SysOM)

Purpose:
    Use the SysOM SDK to create a Cluster VPC Endpoint Connection for the
    target ACK cluster. This is required before SysOM can perform kernel-level
    diagnosis on the cluster.

Usage:
    python scripts/create-cluster-vpc-endpoint-connection.py \\
        --region <region> --cluster-id <cluster_id> [--dry-run]

Arguments:
    --region        ACK cluster region (required)
    --cluster-id    ACK cluster ID (required)
    --dry-run       Optional flag; if present, the API call is performed in
                    dry-run mode and no real connection is created.

Credential resolution:
    Uses the SDK default credential chain (alibabacloud_credentials).
    The chain automatically resolves credentials in this order:
      1. Environment variables (ALIBABA_CLOUD_ACCESS_KEY_ID, etc.)
      2. Credentials file (~/.alibabacloud/credentials)
      3. Aliyun CLI configuration (~/.aliyun/config.json)
      4. Instance metadata (ECS RAM role)
    No explicit AK/SK handling is performed by this script.

Output:
    On success the script prints the API response code 'Success' to stderr.

Pinned dependencies (installed by scripts/setup-sdk.sh into .sysom-sdk-venv):
    alibabacloud_sysom20231230==1.18.0
    alibabacloud_tea_openapi==0.3.12
    alibabacloud_credentials>=1.0.2
"""
import argparse
import json
import sys


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Create an ACK Cluster VPC Endpoint Connection via the SysOM SDK."
    )
    parser.add_argument("--region", required=True, help="ACK cluster region (required)")
    parser.add_argument("--cluster-id", required=True, help="ACK cluster ID (required)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run in dry-run mode (optional, default: false)",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    try:
        from alibabacloud_credentials.client import Client as CredentialClient
        from alibabacloud_tea_openapi.utils_models import Config
        from alibabacloud_sysom20231230.client import Client
        from alibabacloud_sysom20231230 import models
    except ImportError:
        print(
            "ERROR: SysOM SDK or credentials library is not installed. Run: bash scripts/setup-sdk.sh",
            file=sys.stderr,
        )
        print(
            "  This installs the pinned dependencies "
            "alibabacloud_sysom20231230==1.18.0, alibabacloud_tea_openapi==0.3.12, "
            "and alibabacloud_credentials>=1.0.2 "
            "into the .sysom-sdk-venv virtual environment.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Use the SDK default credential chain — no explicit AK/SK handling.
    credential_client = CredentialClient()

    config = Config(
        credential=credential_client,
        endpoint="sysom.aliyuncs.com",
        user_agent="AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling",
        connect_timeout=10000,
        read_timeout=30000,
    )

    client = Client(config)

    request = models.CreateClusterVpcEndpointConnectionRequest(
        region=args.region,
        cluster_id=args.cluster_id,
        dry_run=args.dry_run,
    )

    try:
        response = client.create_cluster_vpc_endpoint_connection(request)
        response_body = response.body

        if hasattr(response_body, "to_map"):
            result = response_body.to_map()
        else:
            result = {"body": str(response_body)}

        code = result.get("code", "")

        if code == "Success":
            print("[OK] Cluster VPC endpoint connection created successfully.", file=sys.stderr)
        else:
            message = result.get("message", "unknown error")
            print(f"ERROR: Creation failed: {code} - {message}", file=sys.stderr)
            print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)

    except Exception as error:
        print(f"ERROR: API call exception: {error}", file=sys.stderr)
        print(
            "  Verify network connectivity to sysom.aliyuncs.com and that the "
            "credentials have cs:CreateClusterVpcEndpointConnection permission.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
