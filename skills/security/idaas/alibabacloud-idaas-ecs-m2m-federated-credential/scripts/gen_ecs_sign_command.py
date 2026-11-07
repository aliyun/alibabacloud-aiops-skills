#!/usr/bin/env python3
"""Generate a one-line command for the user to run on ECS to obtain a PKCS#7 signature.

Usage: gen_ecs_sign_command.py <idaas_instance_id>

Critical constraints (do not change):
  1) First call PUT /latest/api/token to obtain an IMDSv2 metadata token and include
     it in the request header; hardened instances otherwise reject the request.
  2) audience must be URI-encoded JSON:
     {"aud":"<IDaaS_INSTANCE_ID>","signingTime":<timestamp_in_seconds>}
     Encoded: %7B%22aud%22%3A%22...%22%2C%22signingTime%22%3A...%7D
  3) Generate signingTime when the command runs on ECS ($(date +%s)). Do not
     generate it in advance elsewhere, since the signature can expire.
"""
import re
import sys

CMD_TEMPLATE = (
    '(ECS_IMDS_HEADER=X-aliyun-ecs-metadata-token; '
    'ECS_IMDS_VALUE=$(curl -fsS --connect-timeout 3 --max-time 10 -X PUT '
    '-H "$ECS_IMDS_HEADER-ttl-seconds:1200" '
    '"http://100.100.100.200/latest/api/token") && '
    '[ -n "$ECS_IMDS_VALUE" ] && '
    'curl -fsS --connect-timeout 3 --max-time 10 '
    '-H "$ECS_IMDS_HEADER: $ECS_IMDS_VALUE" '
    '"http://100.100.100.200/latest/dynamic/instance-identity/pkcs7'
    '?audience=%7B%22aud%22%3A%22{iid}%22%2C%22signingTime%22%3A$(date +%s)%7D")'
)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: gen_ecs_sign_command.py <idaas_instance_id>")
    iid = sys.argv[1]
    if not re.fullmatch(r"idaas_[a-z0-9]+", iid):
        sys.exit(f"ERROR: Invalid IDaaS instance ID format (expected the idaas_ prefix): '{iid}'")
    print("# Copy the entire command below, run it on ECS, and paste back the PKCS#7 signature.")
    print(CMD_TEMPLATE.format(iid=iid))


if __name__ == "__main__":
    main()
