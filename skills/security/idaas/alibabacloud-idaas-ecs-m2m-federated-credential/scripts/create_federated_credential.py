#!/usr/bin/env python3
"""Create a PKCS#7 application federated credential linking a provider to an M2M client application.

Usage: create_federated_credential.py <region> <instance_id> <app_id> <fcp_id>
                                     <cred_name> <mode> <target> [description]
  mode:   instance = specific ECS instances (target: comma-separated IDs, up to 10).
          account  = cloud account (target: account ID; all ECS instances in it are trusted).
Output: Raw response, followed by AFC_ID=afc_xxx on the final line.
"""
import json
import re
import sys

from common import die, info, run_aliyun, validate_general_name

MAX_INSTANCES = 10


def build_condition(mode: str, target: str) -> str:
    if mode == "instance":
        ids = [x.strip() for x in target.split(",") if x.strip()]
        if not ids:
            die("instance mode requires at least one ECS instance ID")
        if len(ids) > MAX_INSTANCES:
            die(f"Specific-instance mode supports at most {MAX_INSTANCES} ECS instance IDs (received {len(ids)})")
        for i in ids:
            if not re.fullmatch(r"i-[a-z0-9]+", i):
                die(f"Invalid ECS instance ID: '{i}' (expected a value such as i-bp1xxxx)")
        if len(ids) == 1:
            return f"Equals(pkcs7.payload.jsonData.'instance-id', \"{ids[0]}\")"
        parts = ",".join(
            f"Equals(pkcs7.payload.jsonData.'instance-id', \"{i}\")" for i in ids)
        return f"Or({parts})"
    if mode == "account":
        if not re.fullmatch(r"[0-9]{1,32}", target):
            die(f"In account mode, target must be a numeric cloud account ID: '{target}'")
        return f"Equals(pkcs7.payload.jsonData.'owner-account-id', \"{target}\")"
    die(f"mode must be instance or account; received: '{mode}'")


def main() -> None:
    if len(sys.argv) < 8:
        die("Usage: create_federated_credential.py <region> <instance_id> <app_id> "
            "<fcp_id> <cred_name> <instance|account> <target> [description]")
    region, iid, app_id, fcp_id, name, mode, target = sys.argv[1:8]
    validate_general_name(name, "Federated credential name")
    desc = sys.argv[8] if len(sys.argv) > 8 else "Created by skill idaas-ecs-m2m-federated-credential"

    cond = build_condition(mode, target)
    info(f"Verification condition: {cond}")

    d = run_aliyun([
        "eiam", "create-application-federated-credential", "--region", region,
        "--instance-id", iid,
        "--application-id", app_id,
        "--federated-credential-provider-id", fcp_id,
        "--application-federated-credential-type", "pkcs7",
        "--application-federated-credential-name", name,
        "--description", desc,
        "--verification-mode", "freedom",
        "--verification-condition", cond,
    ])
    print(json.dumps(d, ensure_ascii=False))
    afc_id = d.get("ApplicationFederatedCredentialId", "")
    if not afc_id:
        die(f"Failed to create the application federated credential: {d}")
    print(f"AFC_ID={afc_id}")


if __name__ == "__main__":
    main()
