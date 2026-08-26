# Diagnosis Report Template

Render the final diagnosis report for the user following this structure. All values come from the JSON output of `scripts/cloud_native_internet_diag.py` (stdout) and the stderr trace.

## Dual-Layer Script Output

The script itself emits two layers; the rendered report must use both:

1. **Machine layer (stdout JSON)** — structured report for downstream agents/automation. Besides the technical fields it carries three stable user-facing fields:
   - `summary`: a few plain-English sentences for non-technical users (verdict + reason + what to do next).
   - `plain_language_conclusion`: one-sentence verdict.
   - `recommended_actions`: array of next steps (empty when no action is needed).
2. **User layer (stderr)** — `[INFO]` / `[WARN]` / `[ERROR]` progress traces followed by a formatted human-readable report block (Product / Instance / Region / Conclusion / Details / How it works / Next steps). Jargon is explained in plain language (e.g. NAT/SNAT is introduced as "a managed translator that lets private workloads go out through a fixed public IP"). Degraded paths (permission denied, instance not found, invalid parameters) still print both layers with an actionable summary — never a bare error code.

When rendering for a non-technical user, quote the stderr report block and the `summary`; when feeding the next agent stage, pass the stdout JSON as-is.

### Dual-Layer Example (FC quadrant D, NAT SNAT hit)

stdout (excerpt):

```json
{
  "success": true,
  "fc_quadrant": "D",
  "egress_check": { "has_public_egress": true },
  "summary": "This FC function CAN access the internet through a fixed public IP 121.40.254.46 (NAT gateway SNAT). No action needed.",
  "plain_language_conclusion": "Internet access works through fixed public IP 121.40.254.46.",
  "recommended_actions": []
}
```

stderr (excerpt, appended after the `[INFO]` traces):

```
================================================================
Public Internet Egress Diagnosis Report
================================================================
  Product  : Function Compute (FC)
  Instance : eval-quad-d-vpc
  Region   : cn-hangzhou
  VPC      : vpc-bp136rn5gl8reiglsvexg
  vSwitch  : vsw-bp1lmvl9ivca20u5uqrds
  FC mode  : quadrant D (internetAccess=false)
----------------------------------------------------------------
  Conclusion:
    Internet access works through fixed public IP 121.40.254.46.

  Details:
    This FC function CAN access the internet through a fixed
    public IP 121.40.254.46 (NAT gateway SNAT).
    No action needed.

  How it works:
    The instance sits on a private network (VPC). To reach the
    internet it needs an exit route; the common one is a NAT
    gateway with a SNAT rule - a managed translator that lets
    private workloads go out through a fixed public IP.

  Next steps: none - no action needed.
================================================================
```

## Template

```
============================================================
Cloud-Native Product Public Internet Egress Diagnosis Report
============================================================

[Product Information]
  Product       : <product_name, e.g. Cloud-native Gateway (MSE)>
  Instance ID   : <instance_id>
  Region        : <region>
  VPC ID        : <vpc_id or (not configured)>
  vSwitch ID    : <vswitch_id or (not bound)>

[Function Compute Network Config]   <- FC only
  internetAccess : <true/false>
  VPC config     : <configured / not configured>
  Quadrant       : <A / B / C / D>
  Fixed public IP: <supported (NAT SNAT verified) / not supported>

[Egress Check]                       <- when the NAT/SNAT check ran
  NAT gateways checked : <count>
  Matched SNAT entries : <count>
  SNAT public IP(s)    : <ips or none>

[Diagnosis Conclusion]
  <conclusion field from the JSON output>

[Warnings / Degradations]            <- only when present
  <each [WARN] trace, e.g. authorization errors on sub-queries>

[Information Sources]
  - <API, e.g. mse:GetGateway (2019-05-31)> : <what it contributed>
  - <API, e.g. vpc:DescribeNatGateways (2016-04-28)> : <what it contributed>
  - sts:GetCallerIdentity : caller UID <uid> (auto-derived, if applicable)

[Auto-fill Declarations]             <- only when any parameter was auto-filled
  - e.g. "UID auto-derived via sts:GetCallerIdentity: 1772241626973633"
============================================================
```

## Rendering Rules

1. **Never invent values.** Every field must come from the script JSON output; omit a section when its data is absent (e.g. no `[Egress Check]` for FC quadrants A/B/C).
2. **Preserve errors verbatim.** If the script exits non-zero, the report must contain the exact `error` / `conclusion` text (used for traceability).
3. **Warnings are mandatory.** Every `[WARN]` line emitted on stderr (authorization degradation, gatewayType mismatch) must appear under `[Warnings / Degradations]`.
4. **Information Sources must list every API actually called** in this session with its popVersion, matching the APIs declared in `related_apis.yaml`.
5. **Auto-fill declarations are mandatory** whenever the UID (or any other parameter) was auto-derived; state the source explicitly.
