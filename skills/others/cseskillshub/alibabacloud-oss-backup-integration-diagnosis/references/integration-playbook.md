# Integration Playbook

Configuration-advice playbook for connecting third-party backup software to
Alibaba Cloud OSS. All guidance is advisory: this skill never executes a
change, never modifies buckets/RAM/tools, and never submits whitelist
requests on the user's behalf.

Sources: official OSS documentation (see `s3-compat-notes.md` and
`retrieval-fee-guide.md`) plus 170 matched real support tickets
(ticket/oss07.xlsx): third-party backup tools 38, S3-compat config 27,
Veeam whitelist 23, retrieval-fee attribution 23, V1-signature adaptation 22,
rclone 5, Synology/NAS 4.

## Track 1 — Tool connection checklist (works for every tool)

1. Endpoint form: S3-compatible endpoint
   `https://s3.oss-{region}.aliyuncs.com` (public),
   `https://s3.oss-{region}-internal.aliyuncs.com` (same-region VPC),
   `https://s3.oss-accelerate.aliyuncs.com` (transfer acceleration).
   Always include the `https://` scheme.
2. Request style: virtual-hosted only. Bucket name must be a subdomain
   (`<bucket>.<endpoint>`); OSS rejects path-style URLs.
3. Signature version: V4. OSS is phasing out V1; requests signed with V1
   are rejected with `V1 signature is forbidden`. V4 additionally requires
   the bucket region ID in the client configuration.
4. Credentials: a dedicated RAM user with least-privilege actions
   (typically `oss:PutObject`, `oss:GetObject`, `oss:ListObjects`,
   `oss:ListParts`, `oss:AbortMultipartUpload` plus `oss:GetBucketInfo`
   for connection validation). Never the account root AccessKey.
5. Region consistency: endpoint, configured region and bucket must all
   belong to the same region.

## Track 2 — Veeam Backup & Replication

- The target bucket must be registered in the Veeam compatibility whitelist
  before first use. Provisioning is a manual Alibaba Cloud backend action;
  the customer cannot self-serve. Guidance: submit a support ticket with
  account UID, bucket name(s), region(s) and Veeam version, then re-run the
  repository validation after provisioning.
- Objects written by Veeam are stored in a proprietary chunked format;
  direct download via ossbrowser/ossutil/S3 client is not restorable.
  Restore must go through the Veeam console.
- Repository validation errors `V1 signature is forbidden`: enable V4 and
  set the bucket region (Track 3).

## Track 3 — V1-signature adaptation (error routing)

Trigger messages: `V1 signature is forbidden`, `V1 signature has been
disabled`.

1. Upgrading the tool/SDK version alone is NOT enough — the client must
   explicitly enable the V4 signature (ticket-verified root cause).
2. V4 requires the region ID (e.g. `cn-hangzhou`) at client
   initialization; legacy configs without a region fail after the switch.
3. Minimum V4-capable versions (official table): OSS SDK Java >= 3.17.4,
   Python V1 >= 2.18.4 (Python V2 all versions), Go V1 >= 3.0.2 (Go V2 all),
   PHP V1 >= 2.7.0, C# V1 >= 2.14.0, JavaScript >= 6.20.0, C++ >= 1.10.0,
   C >= 3.11.0, Objective-C (iOS) >= 2.11.1, Android >= 2.3, Swift (all
   versions), ossutil1.0 >= 1.7.12, ossfs1.0 >= 1.91.4; ossutil2.0 /
   ossbrowser2.0 / ossfs2.0 support V4 in all versions; ossbrowser1.0 has no
   V4 support at all.
4. Tools with no V4 path: open a support ticket; do not attempt to bypass
   the signature policy.

## Track 4 — Retrieval / minimum-duration fee attribution

See `retrieval-fee-guide.md`. Backup workloads are the classic generator of
surprise retrieval bills because they read back (verify) and rotate
(overwrite/delete) objects automatically.

## Track 5 — Officially documented alternative paths

When a third-party tool is not required, the official documentation offers
native routes worth naming before deep tool troubleshooting:

- **Cloud Backup (HBR) scheduled backup of a bucket**: periodic
  incremental backup of objects with custom cycles (hour/day/week/month)
  and prefix scope, restorable from backup vaults (official doc:
  configure-scheduled-backup). This is the native answer to "how do I back
  up this bucket" without third-party software.
- **OSS Backint Agent for SAP HANA**: official agent streaming HANA
  backups to OSS through the SAP Backint interface (install script +
  oss-backint-agent.ini configuration + SQL enablement). For SAP HANA
  backup-to-OSS tickets, prefer this official agent over generic S3-compat
  guidance.
- **Veeam**: the official doc confirms the bucket whitelist ticket
  requirement (Track 2) and shows the repository wizard path
  (Object storage -> S3 Compatible -> Service point / Region /
  Credentials -> Bucket / Folder).

## Track 6 — Escalation wording (out of scope)

- Executing the whitelist provisioning, modifying bucket/RAM/tool
  configuration, refunds for already-billed retrieval fees, or data
  restore operations are NOT performed by this skill. Wording: "This
  diagnosis is configuration advice only. To execute the change, provision
  the whitelist, or dispute the fee, please submit a support ticket with
  the details above."
