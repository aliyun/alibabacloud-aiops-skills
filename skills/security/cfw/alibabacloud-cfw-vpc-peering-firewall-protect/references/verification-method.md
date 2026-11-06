# Verification Method

Step-by-step verification of every subcommand. All operations are verified against the live API state;
a success response alone is never treated as proof (the switch and modify APIs return only a RequestId).

## Environment check

```bash
bash scripts/validate-cli.sh --check-permission
```

Expected: `cli_installed=true`, `cli_version_ok=true`, `auto_plugin_install=true`,
`credential_valid=true`, `permission_check=true`. Any `false` -> follow the remediation in SKILL.md
section Check CLI Environment before proceeding.

Before a create/assess that relies on route auto-discovery:

```bash
bash scripts/validate-cli.sh --check-permission --mode create --region cn-hangzhou
```

Expected: `create_mode_ready=true`. If `false`, either grant the missing `vpc:Describe*` permissions or
pass `--local-cidr-json` / `--peer-cidr-json` to create.

## query

```bash
bash scripts/vpc-fw-switch.sh query --region cn-hangzhou
```

Verify: the JSON contains a `VpcFirewalls` array and `TotalCount`. Each entry has `VpcFirewallId`,
`FirewallSwitchStatus`, `LocalVpc.VpcId`, `PeerVpc.VpcId`, `ConnectSubType`. Filter with `--status`,
`--vpc-id`, `--connect-subtype`, `--vpc-firewall-id`, `--vpc-firewall-name`. Present results as a
Markdown table (SKILL.md section Query). An empty `VpcFirewalls` is a valid result - report it
explicitly, do not stay silent.

## detail

```bash
bash scripts/vpc-fw-switch.sh detail --vpc-firewall-id vfw-example0001
```

Verify: the response carries `LocalVpc` / `PeerVpc` with `EniId`, `RouterInterfaceId`,
`VpcCidrTableList`, plus `FirewallSwitchStatus`. This is the authoritative source for the route tables
used by `update`.

## enable / disable (three-phase)

1. **Impact preview** - query the firewalls to be switched (`--status closed` for enable, `--status
   opened` for disable) and show the affected list + the 5~30 minute / long-connection-flap warning.
2. **Execute** - after explicit user confirmation:
   ```bash
   bash scripts/vpc-fw-switch.sh enable --vpc-firewall-ids "vfw-example0001"
   bash scripts/vpc-fw-switch.sh disable --vpc-firewall-ids "vfw-example0001,vfw-example0002"
   ```
   Verify: the output JSON lists the ID under `succeeded`. A `failed` entry carries the error code.
3. **Result verification** - poll the query command until the status settles:
   ```bash
   bash scripts/vpc-fw-switch.sh query --vpc-firewall-id vfw-example0001
   ```
   Expected transition: enable -> `closed` -> (transitional) -> `opened`; disable -> `opened` ->
   (transitional) -> `closed`. Because route re-learning takes **5~30 minutes**, poll every 30 seconds for
   up to 30 minutes. If the target status is not reached, tell the user to confirm in the console rather
   than re-submitting the switch blindly.

Dry-run to preview the exact CLI call without executing:

```bash
bash scripts/vpc-fw-switch.sh enable --vpc-firewall-ids "vfw-example0001" --dry-run
```

## assess

```bash
# inventory
bash scripts/vpc-fw-lifecycle.sh assess --region cn-hangzhou
# single-pair plan
bash scripts/vpc-fw-lifecycle.sh assess --local-vpc-id vpc-example0001 --local-region cn-hangzhou \
    --peer-vpc-id vpc-example0002 --peer-region cn-hangzhou
```

Verify: inventory mode returns `configured` and `protectable` arrays; plan mode returns `actionable`,
`precheck` (with `items` / `failed_items`), `discovered_routes` (`local` / `peer` / `masked32`), `risks`,
and a `command` template that **omits `--yes`** (creation must be confirmed first). Whenever `actionable`
is `false`, `do_not_execute` is `true` and `resolve_first` lists the blockers to clear. The assessment is
read-only - it never changes state.

## precheck

```bash
bash scripts/vpc-fw-lifecycle.sh precheck --local-vpc-id vpc-example0001 --local-region cn-hangzhou \
    --peer-vpc-id vpc-example0002 --peer-region cn-hangzhou
```

Verify: `status` is `pass` when `failed_items` is empty. Each item has a `display` label - present every
item using it. On `fail`, resolve each blocking item before creating.

## create

```bash
bash scripts/vpc-fw-lifecycle.sh create --local-vpc-id vpc-example0001 --local-region cn-hangzhou \
    --peer-vpc-id vpc-example0002 --peer-region cn-hangzhou \
    --vpc-firewall-name vpc-fw-prod --firewall-switch close --yes
```

Without `--yes` the command stops at a hard gate: exit 2, `error_code=ConfirmationRequired`, a
`command_preview` holding the exact `CreateVpcFirewallConfigure` call, and **no** API request sent. That
is the expected result of a first pass - show the preview to the user, get an explicit confirmation, then
re-run the same command with `--yes`. `--dry-run` prints the preview and exits 0 without sending anything
either.

Verify after a real create: the output JSON contains a non-empty `vpc_firewall_id`. Then poll the query
command until the firewall appears with status `closed` (creation takes ~5 minutes). If
`--firewall-switch open` was used, poll until `opened` (5~30 minutes).

## update (auto-verified)

```bash
bash scripts/vpc-fw-lifecycle.sh update --vpc-firewall-id vfw-example0001 --vpc-firewall-name new-name
```

Verify: the output JSON carries `verification.verified=true`. The script reads the current name and both
CIDR table lists from the detail API, applies the change, then re-reads via the list API (up to 3 tries)
to confirm the new name. A `VerifyFailed` result (exit 2) means the live state did not match - re-query
before retrying.

## engine ips / engine acl-engine

```bash
# read-only: no write flag
bash scripts/vpc-fw-engine.sh ips --vpc-firewall-id vfw-example0001
bash scripts/vpc-fw-engine.sh acl-engine --vpc-firewall-id vfw-example0001
# preview the exact modify command without executing it
bash scripts/vpc-fw-engine.sh ips --vpc-firewall-id vfw-example0001 --run-mode 0 --dry-run
# write, only after the user confirmed the preview
bash scripts/vpc-fw-engine.sh ips --vpc-firewall-id vfw-example0001 --run-mode 0 --yes
bash scripts/vpc-fw-engine.sh acl-engine --vpc-firewall-id vfw-example0001 --strict-mode 1 --yes
```

Verify each step:

1. **Read** - `success=true` and `mode=get`. `configured` tells you whether the numbers are live or
   only the account defaults of a `notconfigured` firewall, and `source_api` names the API they came
   from: `DescribeVpcFirewallDefaultIpsConfig` when the dedicated read answered, `DescribeVpcFirewallList`
   when it fell back. Surface that distinction instead of presenting defaults as the current setting.
2. **Preview without `--yes`** - exit 2 with `error_code=ConfirmationRequired` and a `command_preview`
   holding the exact modify command. stderr carries the current-to-target diff and, when the change
   weakens protection, a `PROTECTION DOWNGRADE` line. No modify call is made - assert that.
3. **`--dry-run`** - exit 0 and stdout is only the modify command. Still no modify call.
4. **Write with `--yes`** - `success=true`, `mode=set`, `previous` and `applied` blocks, a `downgrades`
   array and `verification.verified=true`. Both modify APIs return only a RequestId, so the script
   re-reads the value up to 3 times; `VerifyFailed` (exit 2) means the live value never matched.
5. **Omitted fields are preserved** - request one field only and check the `applied` block still carries
   the other three unchanged. The IPS modify API requires all four, and this fill-in is what stops a
   partial request from silently resetting the rest.
6. **Wrong enums never reach the API** - `--run-mode 2`, `--rule-class 9` or `--strict-mode yes` exit 1
   with a local validation message and make no API call at all.
7. **Unconfigured firewall** - a write on a `notconfigured` firewall exits 2 with `FirewallNotConfigured`
   before any modify call, even under `--dry-run`.
8. **Unknown firewall** - `ErrorVpcFirewallNotFound`.

There is no transition to wait for: unlike the switch, an engine change takes effect immediately, so the
read-back normally verifies on the first attempt. The 3 tries with a 2 second gap only cover replication
lag.

## delete (disabled)

```bash
bash scripts/vpc-fw-lifecycle.sh delete --vpc-firewall-id vfw-example0001
```

Verify: the command exits non-zero with `error_code=DeletionDisabled`, prints the console release path,
the assets that are NOT reclaimed, and (with an ID) a read-only impact report. It never calls the
destructive API.

## Offline regression suite

```bash
bash tests/run_unit_tests.sh
```

Runs with no credentials and no API calls; must stay green after any script change.
