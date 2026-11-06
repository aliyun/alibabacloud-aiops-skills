# Acceptance Criteria

Correct vs incorrect usage patterns and the acceptance checklist a change to this skill must satisfy.

## Scope boundary

| In scope | Out of scope |
|---|---|
| VPC boundary firewall for Express Connect / VPC peering (`DescribeVpcFirewallList` family) | CEN-based VPC firewall (`DescribeVpcFirewallCenList` / `ModifyVpcFirewallCenSwitchStatus`) |
| Query, detail, enable/disable switch, assess, pre-check, create, update (rename/CIDR) | Deleting/releasing the firewall (console-only) |
| Engine settings of one firewall: IPS defense config (`ModifyVpcFirewallDefaultIpsConfig`) and ACL engine mode (`ModifyVpcFirewallAclEngineMode`) | ACL policy rules themselves, IPS rule content, and any CFW setting outside the VPC boundary firewall |
| IPv4 east-west traffic between two peered VPCs | IPv6, `100.64.0.0/10`, cross-region/cross-account, VPC-to-VBR |

## Correct patterns

- **Always present query results as a Markdown table** with paired status semantics
  (`opened（防护开启）` / `closed（防护关闭）`), never raw JSON, never prose-only.
- **Always run the three-phase switch workflow**: impact preview -> explicit confirmation -> execute ->
  poll-to-verify. A bare `ModifyVpcFirewallSwitchStatus` RequestId is NOT proof the switch finished.
- **Warn about the 5~30 minute route re-learning and the long-connection flap** before every enable and
  disable, and recommend off-peak hours.
- **Assess before create.** Use `assess --local-vpc-id ... --peer-vpc-id ...` to get the pre-check and the
  ready-to-run command; only create after the pre-check passes or the user accepts the risk.
- **Take every required parameter from the user.** Never default a VPC ID, region, name, or the switch
  state from a documentation example - examples are syntax illustrations only. When one is missing or
  ambiguous, STOP and ask.
- **Full resource IDs in every clarification option** - never truncated or ellipsized
  (`vpc-example0001（prod-vpc）`, not `vpc-exam...`).
- **Create with the switch closed by default** unless the user explicitly asks to open immediately.
- **Poll the query command after create/switch** to confirm the final state; report partial results honestly.
- **Read the engine settings before changing them.** Both `vpc-fw-engine.sh` subcommands are read-only
  until a write flag appears; run the read (or the write without `--yes`) first and show the
  current-to-target diff.
- **Disclose every protection downgrade before asking for confirmation** - a lower IPS defense mode or
  rule group, a capability switched off, or `strict-mode` strict to loose. Say what the user loses in
  plain language, not just the numeric change.
- **Let the script fill the omitted IPS fields.** `run-mode`, `basic-rules` and `enable-all-patch` are
  required by the IPS modify API, so passing only the field the user named is a CLI error at best and a
  silent reset at worst.
- **Send `--rule-class` only when the user asked for the rule group.** The service couples it to
  `run-mode`: observe mode always stores `0`, and block mode normalizes an explicit `0` to `3` while
  preserving the current group when the flag is omitted. Echoing a stale value can move the group.

## Incorrect patterns (must be rejected)

- Calling the destructive delete API anywhere, or "working around" the delete lockdown with a raw
  `aliyun Cloudfw DeleteVpcFirewallConfigure` call. The skill only prints console guidance.
- Guessing a `/32`-masked route is fine and enabling anyway - enabling interrupts that CIDR.
- Passing `--version` to a Cloudfw/Vpc plugin call (the plugin manages the version and rejects overrides).
- Using `PageNo` for `DescribeVpcFirewallList` (it paginates with `CurrentPage`).
- Treating an empty query result as silence instead of reporting "no matching firewalls".
- Deleting or modifying the Cloud-Firewall-created route entries or the `Cloud_Firewall_Security_Group`.
- Bundling the target-pair question with the switch state / name into one leading question - present the
  plan, then ask a single neutral confirmation.
- Hand-building `aliyun Cloudfw modify-vpc-firewall-default-ips-config` with only the field the user
  mentioned - the required fields are rejected rather than preserved, and a `--rule-class` carried over
  from an old read can silently change the rule group.
- Treating a `configuring` status as an invalid enum and aborting the post-create poll. It is a real
  transitional state; keep polling until `closed` or `opened`.
- Presenting the `IpsConfig` / `AclConfig.StrictMode` of a `notconfigured` firewall as its current
  setting. Those are account defaults; the script labels that case `"configured": false`.
- Reporting an engine change as done from the modify response. Both engine modify APIs return only a
  `RequestId`; only the read-back proves the value changed.
- Running an engine write on a `notconfigured` firewall - it has no engine instance and the API rejects
  its ID with `ErrorParametersFirewallId`. Create and open the firewall first.

## Acceptance checklist for a change

1. `bash tests/run_unit_tests.sh` is green (no credentials, no API calls).
2. Every API the scripts call (`call_cfw_api` / `call_vpc_api`) is declared in the RAM permission list,
   including fallbacks.
3. Every subcommand appears in BOTH the SKILL.md Operation Routing table and the Script Reference table.
4. Every error code handled by `diagnose_cfw_error` is documented in the API error reference.
5. The frontmatter `description` covers the capability trigger keywords in both English and Chinese.
6. Real account resource IDs are split by audience. `SKILL.md`, `references/*` and `scripts/*` ship to
   every user, so they must stay generic - placeholders only (`example` / `xxx` / all-zero suffixes),
   enforced by guard D7. The eval fixtures are the deliberate exception: they run against one specific
   evaluation account, and a placeholder there would exercise nothing, so they name real assets. Every
   ID in `evals/` must be listed in `tests/eval-assets.json` or be an obvious placeholder (guard E4);
   update that inventory first when an asset is rotated or released.
7. The delete API is never invoked; `delete --yes` still refuses with `DeletionDisabled`.
8. Both API wrappers inject the session User-Agent; the session-id is 32-char lowercase hex, generated
   once per session, and the User-Agent also carries `skill-version/<version>`. Generation must not
   depend on `uuidgen` being installed: with that binary absent from `PATH` every script still runs and
   still emits a well-formed User-Agent, and with neither `uuidgen` nor `od` usable the library aborts
   with exit code 1 **before** any API call instead of dying silently.
9. `bash -n` passes on every script; SKILL.md stays within the platform line/description limits.
10. The skill manifest exists with a top-level non-empty string `version`, and it is the single source of
    the `skill-version` User-Agent segment. When the manifest is missing, unreadable, or has no valid
    `version`, every script aborts with exit code 1 **before** any Alibaba Cloud API call is made.
11. An engine write is only reachable through `--yes` after a preview: without it the script exits 2
    with `ConfirmationRequired` and makes no modify call, and `--dry-run` makes none either. The
    read-back verification reports `VerifyFailed` rather than claiming success.
12. SKILL.md body and `references/*.md` carry no non-ASCII outside the exempt zones (frontmatter
    `description`, fenced code blocks, inline code); `scripts/*` carry no non-ASCII at all. Localized
    console labels the user needs to see live in SKILL.md inline code, never in script output.
13. The engine read-back verification compares against the value the service will actually store, not
    the value the caller asked for: `--rule-class` is omitted from the modify call unless the caller
    passed it, the expected `RuleClass` is derived from the `RunMode`/`RuleClass` coupling, and a
    divergence surfaces as `rule_class_derived_by_service` in the output rather than as a failure.
