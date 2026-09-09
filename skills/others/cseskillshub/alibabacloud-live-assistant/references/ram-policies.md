# RAM Policies (Read-Only)

This skill only calls Describe-class (read-only) Live APIs plus the identity
self-check. Grant the following exact actions — no wildcards are needed and
no write actions are ever required.

## Minimum policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "live:DescribeLiveDomainConfigs",
        "live:DescribeLiveDomainMapping",
        "live:DescribeLiveDomainLog"
      ],
      "Resource": "*"
    }
  ]
}
```

## Action → usage mapping

| Action | Used by | Purpose |
|--------|---------|---------|
| `sts:GetCallerIdentity` | credential self-check (`aliyun sts get-caller-identity`) | Verify the CLI default credential chain works before cloud queries |
| `live:DescribeLiveDomainConfigs` | `live_stream_url_generator.py`, `live_theft_handler.py` | Read the `aliauth` (URL authentication) configuration of a live domain |
| `live:DescribeLiveDomainMapping` | `live_stream_url_generator.py` | Resolve the ingest (publish) / playback (vhost) domain pair from either domain |
| `live:DescribeLiveDomainLog` | `live_theft_handler.py` | List offline access-log download URLs for a time window (traffic-theft forensics) |

## Read-only declaration

- This skill is **read-only**: it never calls mutating APIs. Do NOT grant any
  configuration-changing Live actions for this skill, e.g. `live:Add*`,
  `live:Set*`, `live:Update*`, `live:Delete*`, `live:Stop*`.
- The three local-only scripts (`live_quality.py`, `live_node.py`,
  `live_recorder.py`) make no cloud API calls at all and therefore need no
  RAM permissions; the only local writes are user-specified recording /
  snapshot output files.
- On `Forbidden` / `NoPermission` errors the scripts surface the CLI error
  message in their JSON output; record the missing action and point the user
  to this policy document.
