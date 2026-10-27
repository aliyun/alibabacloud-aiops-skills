#!/usr/bin/env python3
"""Bounded SDK fallback for verified EIAM reads when CLI support is unavailable.

Dependencies are pinned in the adjacent requirements.txt. Provision them before
restricted no-install tasks; this reader never installs packages or plugins.
Requires alibabacloud-tea-openapi==0.4.6, alibabacloud-credentials==1.0.12,
and alibabacloud-tea-util==0.3.15.
"""

import argparse
import json
from pathlib import Path
import re
import sys


ACTIONS = (
    "GetIdentityProvider",
    "GetIdentityProviderUdPullConfiguration",
    "GetIdentityProviderUserProfileMapping",
    "GetIdentityProviderAuthnConfiguration",
    "GetNetworkAccessEndpoint",
    "ListSynchronizationJobs",
    "GetSynchronizationJob",
    "ListOrganizationalUnits",
    "ListUsers",
    "GetUser",
)
IDP_ACTIONS = {"GetIdentityProvider", "GetIdentityProviderUdPullConfiguration",
               "GetIdentityProviderUserProfileMapping", "GetIdentityProviderAuthnConfiguration",
               "ListSynchronizationJobs"}
SCOPED_ARGUMENTS = {"GetNetworkAccessEndpoint": "network_access_endpoint_id",
                    "GetSynchronizationJob": "synchronization_job_id",
                    "ListOrganizationalUnits": "parent_id",
                    "ListUsers": "organizational_unit_id", "GetUser": "user_id"}


def read_skill_version():
    manifest = json.loads((Path(__file__).resolve().parents[1]
                           / "references/manifest.json").read_text())
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._+-]{0,63}", version):
        raise ValueError("invalid Skill version")
    return version


def redact(value):
    if isinstance(value, dict):
        return {key: "[REDACTED]" if re.search(
            r"Secret|Password|Token|EncryptKey", key, re.I
        ) else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def request_query(args):
    query = {"InstanceId": args.instance_id}
    if args.action == "ListSynchronizationJobs":
        query.update({"TargetType": "identity_provider", "TargetIds.1": args.idp_id,
                      "PageNumber": str(args.page_number), "PageSize": "100"})
    elif args.action in IDP_ACTIONS:
        query["IdentityProviderId"] = args.idp_id
    elif args.action == "GetNetworkAccessEndpoint":
        query["NetworkAccessEndpointId"] = args.network_access_endpoint_id
    elif args.action == "GetSynchronizationJob":
        query["SynchronizationJobId"] = args.synchronization_job_id
    elif args.action == "ListOrganizationalUnits":
        query.update({"ParentId": args.parent_id, "PageNumber": str(args.page_number), "PageSize": "100"})
    elif args.action == "ListUsers":
        query.update({"OrganizationalUnitId": args.organizational_unit_id,
                      "PageNumber": str(args.page_number), "PageSize": "100"})
    elif args.action == "GetUser":
        query["UserId"] = args.user_id
    return query


def call(args):
    from alibabacloud_credentials.client import Client as CredentialClient
    from alibabacloud_tea_openapi.client import Client
    from alibabacloud_tea_openapi import models
    from alibabacloud_tea_util.models import RuntimeOptions

    # Use the SDK default provider chain; never read or translate CLI profiles.
    client = Client(models.Config(
        credential=CredentialClient(), endpoint=args.endpoint, region_id=args.region,
        user_agent=args.user_agent, connect_timeout=5000, read_timeout=15000,
    ))
    params = models.Params(action=args.action, version="2021-12-01", protocol="HTTPS",
                           method="POST", auth_type="AK", style="RPC", pathname="/",
                           req_body_type="formData", body_type="json")
    return client.call_api(params, models.OpenApiRequest(query=request_query(args)),
                           RuntimeOptions(autoretry=False, max_attempts=1,
                                          connect_timeout=5000, read_timeout=15000))["body"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=ACTIONS, required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--idp-id")
    parser.add_argument("--network-access-endpoint-id")
    parser.add_argument("--synchronization-job-id")
    parser.add_argument("--parent-id")
    parser.add_argument("--organizational-unit-id")
    parser.add_argument("--user-id")
    parser.add_argument("--region", required=True)
    parser.add_argument("--endpoint", required=True, help="Verified EIAM hostname, without scheme")
    parser.add_argument("--user-agent", required=True, help="Current Skill session User-Agent")
    parser.add_argument("--page-number", type=int, default=1)
    args = parser.parse_args()
    required = ["instance_id"]
    if args.action in IDP_ACTIONS:
        required.append("idp_id")
    if args.action in SCOPED_ARGUMENTS:
        required.append(SCOPED_ARGUMENTS[args.action])
    for name in required:
        value = getattr(args, name)
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
            parser.error(name.replace("_", "-") + " is required and must be a valid resource ID")
    if not re.fullmatch(r"eiam\.[a-z0-9-]+\.aliyuncs\.com", args.endpoint):
        parser.error("use a verified regional EIAM API hostname")
    if args.page_number < 1:
        parser.error("page-number must be positive")
    try:
        skill_version = read_skill_version()
    except (OSError, ValueError):
        parser.error("repair references/manifest.json before making cloud calls; a valid version is required")
    if not re.fullmatch(r"AlibabaCloud-Agent-Skills/alibabacloud-idaas-ad-ldap-integration/"
                        r"[0-9a-f]{32} skill-version/" + re.escape(skill_version), args.user_agent):
        parser.error("user-agent must contain a fresh session ID followed by skill-version/<manifest version>")
    try:
        print(json.dumps(redact(call(args)), ensure_ascii=False))
    except Exception as error:
        # Exception messages/data may include request values or credentials.
        safe = {"error_type": type(error).__name__}
        for key in ("code", "request_id", "status_code"):
            value = getattr(error, key, None)
            if value is not None and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", str(value)):
                safe[key] = value
        print(json.dumps(safe), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
