# Execution Phases — index

> **This file is the map, not the manual.** It is deliberately short so it always arrives whole. Each phase
> below names the file that carries its actual steps — read that file when you enter the phase.
>
> ⚠️ Do NOT execute a phase from memory or from this summary alone. The per-phase files hold the exact
> commands, flags, and user-facing copy; this index only tells you the order, the entry/exit conditions,
> and which gates may not be skipped.

## Order of execution

| # | Phase | File | Exit condition (all must hold before moving on) |
|---|-------|------|-------------------------------------------------|
| 1 | **-2 · Settle the SKU** | `sku-resolution.md` | One of the 7 legal SKU names is settled. No SKU ⇒ STOP, never guess. |
| 2 | **-1 · Preconditions** | `preflight.md` | Alibaba Cloud account confirmed + real-name verified + deploy capability taken over. |
| 3 | **-1.5 · CLI reachability gate** | `preflight.md` | Every product in THIS SKU checked against `cli_capability_matrix.md` by **static table read** (no CLI calls); partial/false products opened manually and user-confirmed. |
| 4 | **0 · CLI install** (0.1 / 0.1b) | `cli-install.md` | `aliyun version` >= min_version AND `--auto-plugin-install true` set. |
| 5 | **0 · Credentials** (0.2 / 0.3) | `credential-setup.md` | One profile pinned and authenticating. AK/SK never read or echoed. |
| 6 | **0.2b · Policy coverage probe** | `policy-probe.md` | 🔒 **HARD GATE.** Every product in this SKU's set probed read-only; zero 403 / NoPermission / Forbidden.RAM. Any failure ⇒ STOP and hand over a SKU-scoped whole-policy replacement JSON. |
| 7 | **0.5 · Connectivity** | `credential-setup.md` | `describe-regions` succeeds, proving AssumeRole + trust + policy. |
| 8 | **0.4 · Image resolution** | `image-resolution.md` | `state.resources.ecs.image_id` written and locked. |
| 9 | **1 · Confirm + authorize** | `confirm-authorize.md` | 🔒 Resource list shown + component removal handled + **payment second-confirmation received** + Step 1.5 self-check all green. |
| 10 | **2 · Network infra** | `network.md` | VPC + VSwitch + security group created (free) and tag-backfilled; SSH restricted to `${MY_IP}/32`. |
| 11 | **3 · Create resources** | `provision.md` | 💰 The paid phase. Every yaml step executed, tagged `opc:managed=true`, written to state. |
| 12 | **4 · Verify + wrap-up** | `wrapup.md` | Step 4.6 wrap-up hard-gate all green. Teardown path lives here too. |

## Gates that may never be skipped

1. **SKU GATE** (Phase -2) — no legal SKU token ⇒ no Phase at all. Inferring or self-selecting a SKU is a critical violation. Offering to install advisor does not lift the STOP.
2. **Reachability gate** (Phase -1.5) — static table read only; running any `aliyun` command to probe reachability here violates iron-rule #25. The first real CLI call is in Phase 0.
3. **Policy coverage probe** (Step 0.2b) — the only thing that catches a too-narrow policy *before* money is spent. Skipping it means discovering `Forbidden.RAM` in the middle of Phase 3, after earlier paid products already succeeded. Not optional, not "nice to have".
4. **PAYMENT GATE** (Phase 1, SKILL.md Hard Gate #1) — the verbatim charge prompt plus an explicit affirmative reply, immediately before the first fee-incurring call. Earlier deploy-intent replies are NOT authorization.
5. **Pre-execution self-check** (Step 1.5) — every item green before Phase 3, including item 3 (the probe passed).
6. **Wrap-up gate** (Step 4.6) — every section present before the session ends.

## Cross-cutting references

- **Iron rules + credential red lines** → `iron-rules.md`
- **CLI plugin-mode flag conventions** (`--biz-region-id` required, tag syntax, `--output` quoting, `ossutil ls`, esa `--endpoint`) → `cli-meta.md` · read this before writing any new CLI command
- **RAM least-privilege policy + per-SKU scoping** → `ram-policies.md`
- **Product CLI reachability matrix** → `cli_capability_matrix.md`
- **Per-SKU step definitions** → `sku-params/<sku>.yaml`, format spec in `sku-params-format.md`
- **Image family reference** → `image_families.md`

## Numbering notes

- Phase **-2** (settle the SKU) runs first even though its number looks odd — it must precede Phase -1.5,
  which needs the SKU.
- **Step 0.5** is the connectivity check (in `credential-setup.md`); **Phase 0.4** is image resolution (in
  `image-resolution.md`) — two different things.
