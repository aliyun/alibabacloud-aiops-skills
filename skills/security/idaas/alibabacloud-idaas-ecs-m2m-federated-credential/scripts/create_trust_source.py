#!/usr/bin/env python3
"""Create an ECS PKCS#7 federated credential provider.

Trust anchor: Alibaba Cloud's official certificate. Conditions: cloud account and instance aud.

Usage: create_trust_source.py <region> <instance_id> <provider_name> <account_id> [validity_seconds]
  provider_name: Lowercase letters, digits, underscores, and hyphens only; <=64 characters.
  account_id:    ECS owner account ID (the current account or another account supplied by the user).
  validity:      Signature validity in seconds; default: 3600.
Output: Raw response, followed by FCP_ID=fcp_xxx on the final line.

Plugin mode accepts the PKCS#7 configuration as one typed JSON object with wire
field names. The CLI serializes it to the API's flat request parameters and selects
POST from metadata. Subprocess arguments preserve multiline certificates safely.
"""
import json
import re
import sys

from common import CERT_FILE, die, load_cert, run_aliyun, validate_provider_name


def main() -> None:
    if len(sys.argv) < 5:
        die("Usage: create_trust_source.py <region> <instance_id> <provider_name> "
            "<account_id> [validity_seconds]")
    region, iid, name, account = sys.argv[1:5]
    validity = sys.argv[5] if len(sys.argv) > 5 else "3600"

    if not re.fullmatch(r"idaas_[a-z0-9]+", iid):
        die("Invalid IDaaS instance ID format (expected idaas_[a-z0-9]+)")
    validate_provider_name(name)
    if not re.fullmatch(r"[0-9]{1,32}", account):
        die(f"Cloud account ID must contain only digits: '{account}'")
    if not re.fullmatch(r"[0-9]{1,7}", validity):
        die(f"Signature validity must be seconds expressed as digits: '{validity}'")

    cert = load_cert()
    trust_condition = (
        f"And(Equals(pkcs7.payload.jsonData.'owner-account-id', \"{account}\"),"
        f"Equals(pkcs7.payload.jsonData.audience.aud, \"{iid}\"))"
    )

    d = run_aliyun([
        "eiam", "create-federated-credential-provider",
        "--region", region,
        "--instance-id", iid,
        "--federated-credential-provider-type", "pkcs7",
        "--federated-credential-provider-name", name,
        "--pkcs7-provider-config", json.dumps({
            "TrustAnchorSource": "alibaba_cloud",
            "CmsVerificationMode": "cert",
            "SignatureEffectiveTime": int(validity),
            "SigningTimeValueExpression": "pkcs7.payload.jsonData.audience.signingTime",
            "TrustCondition": trust_condition,
            "Certificates": [{"Content": cert}],
        }),
    ])
    print(json.dumps(d, ensure_ascii=False))
    fcp_id = d.get("FederatedCredentialProviderId", "")
    if not fcp_id:
        die(f"Creation failed (name conflict? Insufficient permissions? Invalid certificate content in {CERT_FILE}?): {d}")
    print(f"FCP_ID={fcp_id}")


if __name__ == "__main__":
    main()
