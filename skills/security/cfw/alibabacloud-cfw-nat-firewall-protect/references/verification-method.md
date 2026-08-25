# Verification Method - CFW NAT Firewall Protection

How to verify that each step of this Skill actually took effect. Two layers:

- **Layer 1 - verify the Skill itself** (offline, no credentials): `bash tests/run_unit_tests.sh`
- **Layer 2 - verify a live operation** (per subcommand, below)

> **Why this file exists:** several CFW NAT firewall APIs return success without doing anything
> (`SwitchSecurityProxy` / `DeleteSecurityProxy` / `UpdateSecurityProxy` accept non-existent
> ProxyIds silently). A successful API response is therefore NEVER proof - only a follow-up read
> is. The scripts embed these verifications; this document states what they check so a human can
> reproduce or audit them.

## Environment Pre-check

```bash
# 1. CLI version (must be >= 3.3.3) + credentials + a real CFW business-API permission probe
bash scripts/validate-cli.sh --check-permission

# 2. Manual-mode only: probe the VPC WRITE permissions without creating anything
bash scripts/validate-cli.sh --check-permission --mode manual --region cn-hangzhou
```

Pass criteria:

| Field | Expected | If not |
|---|---|---|
| `cli_installed` / `cli_version_ok` | `true` | Install or upgrade the CLI (`--install-guide`) |
| `credential_valid` | `true` | Only means a profile exists in `aliyun configure list` |
| `permission_check` | `true` | The authoritative check - calls `DescribeSecurityProxy`; `false` means invalid AK or missing `yundun-cloudfirewall:DescribeSecurityProxy` |
| `manual_mode_ready` (manual probe) | `true` | Each action is reported `granted` / `missing` / `unknown`; grant every `missing` action (RAM prefix is `yundun-cloudfirewall`, NOT `cloudfw`) |

Never print AK/SK. `aliyun configure list` is the only inspection command.

## Step 1: Verify the assessment / plan

```bash
bash scripts/nat-fw-lifecycle.sh assess --region cn-hangzhou
bash scripts/nat-fw-lifecycle.sh assess --region cn-hangzhou --nat-gateway-id ngw-xxx
```

Verify:

1. `assessed_at` is the CURRENT time - the report is a point-in-time snapshot; a stale one must not
   be reused after any console change.
2. `quota.used` < `quota.total`, and (single-gateway mode) `plan.quota.sufficient` is `true`.
3. `precheck.status` is `passed` and `precheck.items` has **9** entries (3 groups: account/region 1,
   NAT spec 3, routing policy 5). Zero items with a `passed` status means the server pre-check did
   not run - re-run instead of proceeding.
4. `plan.actionable` is `true` and `plan.command` is populated. When `false`, `plan.blockers`
   explains why and MUST be resolved first.
5. Every `quota_projection` item is `ok` / `warning` / `exceeded`. A `status: unknown` means the
   usage or the limit could not be read (missing `vpc:*` read or `quotas:GetProductQuota`) - do NOT
   present it as safe. Negative `current` values must never appear (they are normalised to
   `unknown`).
6. `notes` records the diversion scope: `diversion scope: N route table(s) carry a route to ngw-xxx`.
   `N = 0` is a blocker (nothing to divert -> `MissingNatRouteEntryList`).

Cross-check against the console: the route entries listed under Firewall Traffic Diversion Configuration -> Select Route Table are
exactly the diversion scope; tables without a route to the gateway do not appear there and are not
compared for consistency.

## Step 2: Verify the creation pre-check

```bash
bash scripts/nat-fw-lifecycle.sh precheck --nat-gateway-id ngw-xxx --region cn-hangzhou --vpc-id vpc-xxx
```

Verify `PrecheckStatus` is `passed` and every group's `FailedCount` is `0`. Present each item with
its requirement-style wording. Note the server pre-check does **not** validate cross-table route
consistency - a green pre-check does not guarantee auto-mode creation succeeds.

## Step 3: Verify creation

```bash
bash scripts/nat-fw-lifecycle.sh create --nat-gateway-id ngw-xxx --region cn-hangzhou \
  --vpc-id vpc-xxx --proxy-name <name> --vswitch-cidr 10.0.3.0/28 --firewall-switch close --yes

# then poll (creation takes ~2~5 minutes per bound EIP)
bash scripts/nat-fw-switch.sh query --region cn-hangzhou --nat-gateway-id ngw-xxx
```

Verify:

| Check | Expected |
|---|---|
| Status transition | `configuring` -> `closed` (or -> `normal` when created with `--firewall-switch open`) |
| `ProxyId` | Present and stable across polls |
| `VSwitchId` | Auto mode: a NEW vswitch inside the CIDR you passed. Manual mode: exactly the `--vswitch-id` you supplied |
| `SnatIpList` | Non-empty (may hold fewer IPs than bound EIPs when the SNAT table uses only some of them) |
| Polling budget | Every 30s, max 15 minutes; still `configuring` after that -> check the console |

A **timeout** on `CreateSecurityProxy` does NOT mean rejection: the backend may have returned HTTP
200. The script retries at most 3 times and re-reads `DescribeSecurityProxy --NatGatewayId` before
each retry to avoid a duplicate firewall. Verify by query, never by the request's exit status.

## Step 4: Verify the protection switch (three-phase workflow)

```bash
# Phase 1 - impact preview
bash scripts/nat-fw-switch.sh query --region cn-hangzhou --status closed
# Phase 2 - execute
bash scripts/nat-fw-switch.sh enable --proxy-ids "proxy-xxx"
# Phase 3 - verify (MANDATORY)
sleep 5 && bash scripts/nat-fw-switch.sh query --region cn-hangzhou --proxy-id proxy-xxx
```

Verify:

- enable: `closed` -> `opening` -> `normal`; disable: `normal` -> `closing` -> `closed`
- Poll every 5s, max 30s total. `opening` / `closing` means accepted but not finished
- **A proxy that does not appear in the query after a switch call = FAILED**, because the API
  accepts unknown ProxyIds silently. Report the RequestId in that case
- `abnormal` -> surface the `Detail` field verbatim

## Step 5: Verify update, and the close-instead-of-delete boundary

```bash
bash scripts/nat-fw-lifecycle.sh update --proxy-id proxy-xxx --proxy-name <new-name> --strict-mode 0
```

- `update` re-reads the proxy and compares `ProxyName` / `StrictMode`, exiting 2 on mismatch. With
  `--skip-verify` (or without `DescribeNatFirewallList`) you MUST confirm manually

**Deletion is disabled by design** - verify that it stays disabled:

```bash
bash scripts/nat-fw-lifecycle.sh delete --proxy-id proxy-xxx --yes   # must REFUSE
grep -rn 'call_cfw_api "DeleteSecurityProxy"' scripts/              # must return nothing
```

Expected: exit code 1 with `error_code: DeletionDisabled`, no write API call, and `--yes` explicitly
reported as not overriding the restriction. To stop protection, verify the close path instead
(`nat-fw-switch.sh disable`, Step 4) - after which the firewall must still be present with status
`closed`, proving the resource was NOT released.

When the user releases the firewall in the console, the read-only report from the same command tells
them what to expect: current status, and the **leftover assets** that are not reclaimed - the
manual-mode vswitch and orphan custom route tables (e.g. `Cloud_Firewall_ROUTE_TABLE`, reusable by
`prepare`). Verify these against the VPC console after their deletion.

## Step 6: Verify route-diff (read-only)

```bash
bash scripts/nat-fw-lifecycle.sh route-diff --region cn-hangzhou --vpc-id vpc-xxx
```

Verify `divergent_entries` matches the console's route tables, `classification` is
`business_topology` / `mixed` / other, and that **nothing changed**: this command only produces an
`alignment_plan`. Re-run `DescribeRouteEntryList` before and after - the entries must be identical.

## Verifying the Skill itself (offline)

```bash
bash tests/run_unit_tests.sh   # 39 assertions, no credentials, no API calls
```

All green is a release gate. Each group pins a defect that shipped once (see the Regression Tests
section in SKILL.md). To confirm the suite still has teeth, mutate a fix in a COPY of the skill and
confirm the matching assertion turns red.

## Common Errors

| Error | Cause | Resolution |
|---|---|---|
| `ErrorAuthentication` | Invalid or expired AK | `validate-cli.sh --check-permission`, then rotate credentials |
| `NoPermission` / `Forbidden.RAM` | RAM action missing (granted per-action for VPC writes) | `validate-cli.sh --check-permission --mode manual` lists ALL missing actions at once, then grant each of them |
| `-360838` / `ErrorNatGatewayNotExist` | Gateway not yet synced into Cloud Firewall | Wait 1~5 minutes or trigger Asset Sync in the console, then retry |
| `MissingNatRouteEntryList` | No route entry points to the NAT gateway | Add a `0.0.0.0/0` route to the gateway first; `assess` reports this as a blocker |
| `ErrorNatCustomRouteEntryDifferent` | Diversion route tables carry different custom entries | Run `route-diff`; prefer manual mode over aligning production routes |
| `ErrorDefaultRouteConflicts` | The chosen manual vswitch's route table already has `0.0.0.0/0` | Bind a freshly created custom route table (`prepare`) |
| `ErrorProxyAlreadyExist` | The gateway already has a firewall (1:1 mapping) | Query it and use the switch workflow instead |
| `unchecked version` | `--version` was passed to a Cloudfw plugin command | Never pass `--version`; the plugin manages the API version internally |
| Empty stdout with exit 1 | Historical defect: a no-match `grep` aborted the error path before `output_error` | Fixed and guarded by tests (group "error extraction"); if it reappears, run the suite |

For the full error-code reference and the creation dependency requirements, see the reference
documents listed in SKILL.md.
