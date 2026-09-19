# Provisioning Resources Fast with the CLI (Agent / Environment / Deployment)

The authoritative source for commands and flags: the `reference/managed-agent.md` of the skill
`bailian-managed-agent` and `bl <command> --help`. This page covers only **ordering, decision
points, and common traps** — it does not duplicate the command tables.

## Route first

CLI is preferred for quick trials and resource provisioning. Follow [cli-api-routing.md](cli-api-routing.md) for the official installer, one update attempt for a missing feature, then API fallback. A CLI limitation is not a service limitation. Customer application integration goes directly to API/SDK.

## Pre-flight checks (once)

Check [RAM policies and workspace authorization](../ram-policies.md) when onboarding an identity or resolving access failures. A matching workspace API key is required for MA calls; RAM grants and workspace membership are separate.

```bash
bl --version
bl auth status --output json   # use masked fields only; login if needed per routing guide
```

Credential priority: `--api-key` > `DASHSCOPE_API_KEY` > the active profile from `bl auth login`.
**Never** write the key into `agents.yaml` or code; other providers reference `${ENV_VAR}`.

## The standard pipeline

```
1. init      bl managed-agent init          # generates the agents.yaml scaffold (no network)
2. edit      modify agents.yaml per needs   # agents / environments / deployments / vaults / memory_stores
3. validate  bl managed-agent validate      # offline validation; always run after editing
4. plan      bl managed-agent plan          # computes the diff online; show it to the user
5. confirm   reuse explicit consent for this unchanged plan; otherwise stop before apply
6. apply     bl managed-agent apply --yes   # changes the remote
7. test-run  bl managed-agent session run --prompt "..."
```

**Hard rule**: add `--yes` only after the user has seen the `plan` diff and explicitly confirmed;
never add it on your own ahead of time. The same applies to `destroy --yes`, and you must first
tell the user exactly which remote resources will be deleted.

For a preview-only task, showing the plan and stating “not applied” completes the request; do not wait for a reply. If the same unchanged plan already has explicit approval, proceed without asking again. For unattended tasks without approval or required configuration, report the blocker and end; never bypass the gate or start interactive login.

**Scaffold side effect (bl 1.25.0, tested 2026-09-18):** `init --file /tmp/agents.yaml` still updates `.gitignore` in the current working directory. For isolated review or scratch tests, run `init` from a temporary working directory as well; changing only `--file` does not isolate its writes. Inspect the resulting diff before continuing.

## How to provision each resource

| Goal | How | Watch out |
| --- | --- | --- |
| Create an Agent | Add an entry under `agents:` in `agents.yaml` → validate → plan → apply | Agents carry a version number in state; changing config is an update, not a recreation |
| Create an Environment | Declare packages / networking etc. under `environments:` (file mounting does **not** belong here) | Environments only manage sandbox config; the `files:` sub-key under `environments:` is silently ignored by the CLI (no effect, no error). To mount files, use the API / console: `mount_path` starts with `/uploads/`, the real sandbox path is `/mnt/session/uploads/…` (write the real path in the prompt); CLI declarative mounting (top-level `files:` / `deployments.<name>.resources`) was broken in the archived test; re-check after an update before treating it as a current limitation: — validate demands the `/mnt/` prefix while the runtime demands `/uploads/`, a deadlock (field-tested on bl 1.18.1) |
| Create a Deployment | Declare `agent` + `initial_events` under `deployments:` (+ optional `schedule`) | `initial_events` needs at least one `user.message` or `system.message`; `user.define_outcome` is dropped |
| Configure secrets | Declare `vaults:` and have the Agent reference them | Values are injected via environment variables, never stored. Note the sandbox only sees placeholders (`BMA_SECRET_PLACEHOLDER_*`); the egress gateway substitutes the real values per the `allowed_hosts` whitelist (see [../cookbook/08-vault-secret-injection-and-egress-gateway.md](../cookbook/08-vault-secret-injection-and-egress-gateway.md)). Non-sensitive config needs no vault — just pass `environment_variables` at session creation |
| Add MA working memory | Declare `memory_stores:` and bind the Agent using verified current CLI/API fields | Memory Store is launched MA built-in working memory, distinct from UserId-scoped Bailian Memory Library. See [status](../product/status.md); verify current configuration support before execution |
| Adopt existing remote resources | `state import --address <provider.type.name> --remote-id <id>` | Import first, then plan — otherwise plan misjudges it as a "create" |

## Decision points

- **User already has an `agents.yaml`** → do not `init --force` over it. Edit the file directly, or run `state list` first to see what is tracked.
- **User unsure what they want** → start with `init` for a minimal Agent, get one `session run` working, then add environment / memory / scheduling step by step. **Do not generate a big config in one shot.**
- **Deployment or not** → only "scheduled / unattended triggering" needs one; pure conversational integration works with Session alone.
- **Provider scope** → CLI 1.25.0 supports only Bailian for `managed-agent` and rejects other providers; no `--provider` flag is documented on plan. Use an isolated configuration containing only intended resources, and inspect current leaf help instead of adding an unsupported flag.
- **plan shows unexpected changes** → stop and explain the drift (someone changed the remote / a version upgrade / a materialize from an empty remote_id); do not apply directly.

## Test-run and troubleshooting

```bash
bl managed-agent session run --prompt "..." --output json   # get session_id
bl managed-agent session events --session-id <id> --all     # inspect the full event stream to locate the failing step
bl managed-agent skill-list --source all --output json      # pick usable skills
bl managed-agent state list                                 # see tracked resources (offline)
```

Troubleshooting order: **validate (is the config right) → plan (is the remote state right) → session events (which runtime step failed)**.

## Cleanup

- Just stop managing a resource → `state rm` (untracks locally only)
- Actually delete the remote → `destroy --yes` (use `--cascade` when dependencies exist); list what will be deleted for user confirmation before running

## Next steps

After resources work, wire them into your business system → [../tutorials/02-integrate-to-your-system.md](../tutorials/02-integrate-to-your-system.md)
(the first step is swapping the logical names in `agents.yaml` for the remote IDs `agent_xxx` / `env_xxx` — the code side knows IDs, not logical names).

Only need to look up endpoints or fields → [../integration/api-endpoints.md](../integration/api-endpoints.md)

## Readiness before Session creation

**Readiness gate**: an Environment created with preinstalled packages may remain in preparation briefly after creation succeeds. Creating a Session against it during that window can fail. Wait for preparation to finish before creating a bound Session. Use readiness fields only if documented by the current API; do not invent status values. If no readiness signal is exposed, retry only an explicit environment-not-ready rejection with bounded backoff and a total timeout. Reconcile ambiguous request timeouts before retrying Session creation; do not recreate the Environment.

Uploaded files also need time for detection/security review. Wait for each file to become `available` before attaching it at Session creation or mounting it later; stop on rejection or timeout. Creation/upload success alone does not satisfy either readiness gate. See [environment preparation](../tutorials/05-environment-packages.md) and [file scan polling](../tutorials/03-mount-files.md).
