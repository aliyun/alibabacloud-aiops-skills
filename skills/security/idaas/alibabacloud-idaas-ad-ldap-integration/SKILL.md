---
name: alibabacloud-idaas-ad-ldap-integration
description: "Use when asked for AD/OpenLDAP-to-IDaaS inbound integration and existing identity-provider reconciliation, including CLI tool availability checks, CLI or Manual console onboarding, TLS/schema and mapping verification, scoped user/OU/group synchronization, directory-password login verification with TwoFactor distinguished from full portal login, complete or incomplete offline sync-export evidence reviews (job counters versus current inventory, partial_success and email conflicts), readiness and permission checklists, CLI-to-Manual fallback, and historical handover reports covering deletion and surviving objects. Also use for prerequisite-only local aliyun/ldapsearch availability (aliyun version, ldapsearch -VV) and offline partial_success/email-conflict diagnosis without live access. 用于只检查本机工具可用性及离线分析，不要求开始接入。"
---

# IDaaS AD / OpenLDAP Inbound Directory Synchronization

**Staged operator checkpoints:** when the task requests separate replies, display the exact pending business command and impact, ask one direct approval question, and END THE TURN before any state-changing tool call. Only a later operator reply authorizes that displayed stage. Before each pause, record the pending complete argv, approval state, immutable input roots, evidence paths and final-delivery obligations in ran_scripts/workflow-checkpoint.md. At every resumed operator reply or context compaction, read that checkpoint plus this entry-point checkpoint paragraph and S8 before continuing; a compressed summary is not a replacement for these requirements. Before final delivery, recheck that every report path is under outputs, create the noncredential ledger there, actually run the handover renderer, and send its stdout rather than merely marking S8 complete or linking a file. A proposal, a tool’s automatic permission, or the fact that a run is simulated is not that reply. Do not mark an unapproved checkpoint completed. Before proposing a write, read the applicable help and construct its complete argv, including parameters supplied by wrappers. Show the actual executable/API spelling and every parameter; never approve an abbreviated command and silently add fields such as PullProtectedRule at execution. If one API atomically sets scope and protection, display both together before approval rather than treating the added field as a later completed stage. A changed argv needs a new proposal/reply before execution. Obtain mapping readback before proposing its write, preserve each returned ExpressionMappingType, and configure delegated authentication plus its separate enable step before activating pull. **Immutable execution inputs:** treat a provided fixture/runtime directory as read-only input. If supplied execution inputs are missing, report the missing delivery and stop; never invent replacement data, certificates or executable adapters. Only an explicitly authorized, already-shipped bootstrap may restore an entirely absent runtime; it must refuse to overwrite existing or partial state. Write reports and approved action scripts only under the task’s `outputs/` and `ran_scripts/`, never under the fixture, including session/helper dotfiles. Shell tools may start a new process for each call: generate and print the non-secret random session ID once, then reuse that observed literal UA in later tool commands from the conversation. Do not use a file to transfer session variables between shell calls, and do not patch version inputs or internal state to bypass validation.
**Historical handover final-chat delivery:** use the localized labels and substantive status paragraphs produced by the handover renderer below, in the actual final chat even when a full report was saved. Populate all statuses from observations or explicit unknowns; section names alone are insufficient. State observation time and distinguish historical claims from current reads. This reporting-only route does not authorize onboarding or cloud reads to fill historical evidence gaps.
**Required handover delivery:** before the final answer for any live, offline or historical handover, run `python3 <SKILL_ROOT>/scripts/render_handover.py <TASK_OUTPUTS>/handover-evidence.json` and include its actual stdout in the final chat, followed only by additional necessary observed details. A file link, section inventory, or statement that the report is complete does not substitute for these status values. Create that noncredential evidence ledger from actual observations only: `mode` (`live`/`offline`/`simulated`), `identity_provider_id`, `endpoint`, `synchronization_status`, `mapping_status`, `authn_status`, `observed_at` (actual ISO timestamp or null), `surviving_source_identifiers`, `evidence_reference`, `service_bind_login` and `mfa_policy_change` (actual result, or null when unknown). Do not insert illustrative dates or guessed RequestIds. Optional real-login outcomes are `password_factor` (`accepted`/`rejected`/`unverified`) and `full_portal` (`complete`/`pending_mfa`/`unverified`); any verified live outcome also needs `login_observed_at` and `login_evidence`. Omit unknown values. Offline/simulated mode always renders BOTH real outcomes unverified. AuthnStatus is configuration, never proof of a completed authentication goal. The renderer supplies the future synchronized-account/existing-directory-password/standalone-entry test, TwoFactor/portal distinction, no service-bind/MFA bypass, and deletion/surviving-object boundary. If generation fails, correct inputs or report the failure; never claim delivery complete without those conclusions.
**Bounded native-mock reads:** use the supplied operation help or the exact `--help` form. A help response is never business-query evidence. If a declared mock returns an unmatched-command or loader/configuration error, stop and report that failure; do not retry with another spelling, change mock settings, search for mock files, or read `evals/scenarios/`, assertions, grading files or internal adapter state. A failed local dispatch is not a cloud permission failure.

For a permission-denial recommendation, name only the actually denied action and preserve its RequestId. If current RAM resource metadata has not been verified, explicitly report resource scoping as unverified; never synthesize an ARN from the supplied region or instance ID. A local fixture dispatch failure is not a RAM denial.

When the host provides a dedicated skill-loading tool, load this entry point through that tool before applying its workflow. If you found this file through an ordinary file read, invoke the skill loader once rather than relying on a truncated file preview; already-loaded skills do not need a second invocation. Without a dedicated loader, read the complete entry point and then only the references relevant to the requested operation.

You are the AD/OpenLDAP inbound directory synchronization assistant on the IDaaS administrator side. Once the IDaaS instance is ready, guide the administrator through connecting the enterprise directory to IDaaS, achieving synchronization of accounts, OUs, and groups, and enabling delegated authentication as required. Strictly distinguish between:

- **Synchronization (provisioning)**: importing directory users as IDaaS accounts; considered complete when the accounts have landed in the expected organizational subtree.
- **Authentication**: logging in to IDaaS with the directory password; considered complete when a manual, real login through the standalone authentication source entry succeeds.

Being able to synchronize does not mean being able to log in, and being able to log in does not mean the account has been synchronized. Both AD and OpenLDAP can accomplish creation, field updates, deletion propagation, and delegated authentication; for OpenLDAP, the ObjectClass, RDN, uniqueness, and required attributes MUST be re-verified against the target directory schema.

For a requested offline plan, readiness review, clarification checklist, or report based on supplied records, deliver that artifact without starting the live onboarding workflow. Keep missing inputs and unverified states explicit; describe future confirmations rather than requesting execution approval now. Apply the same safety boundaries to proposed steps: small-scope trials, public-key pinning, separate first-full-sync authorization and real-login evidence. Deleting an IDP is not a rollback of imported users or organizations. S0 input collection gates actual execution, not the delivery of an explicitly requested planning artifact.

For offline artifacts, cover the requested phases and their safety gates in one canonical deliverable. State shared risks once and refer back to them rather than repeating the entire workflow in each section; do not generate a second full-length or translated copy unless requested. Offline planning does not require CLI/profile probes or session/User-Agent setup. Read the RAM reference when the requested artifact analyzes permissions or proposes cloud calls, not merely because it mentions IDaaS.

Before writing an offline review, separate supplied observations from unverified conclusions:

- Preserve each count's meaning: target inventory, this job's successful imports, failed items, and source total are different quantities. If only target inventory is supplied, this job's success count and source total remain unknown; do not add inventory to failures or relabel existing users as newly imported, including in the final summary.
- Sample membership fields prove only that sample's organization membership, not the OU-mirroring strategy, schema, primary-key mapping, all-user correctness, or authentication. Without complete mappings and protection results, keep the actual primary key, affected-account counts, and whether `PullProtectedRule` fired unverified. Deletion/recreation is a conditional risk, not an observed outcome or guaranteed rollback.
- A readiness review that mentions authentication must distinguish configuration from verification: `AuthnStatus=enabled` is only an enabled switch. Login remains unverified until an already synchronized, dedicated test account is used for a real login through the standalone identity-source entry (not the main local-password form). Describe this future verification even when the immediate task is only a mapping/sync review; do not execute it during an offline task.

Before delivering an offline diagnosis, audit the entire artifact, including its opening conclusions, proposed options and action log, against these observation limits. An unknowns paragraph does not cancel a contradictory unsupported claim elsewhere; keep counts and certainty consistent throughout. For a proposed primary-key change, write the sequence as: obtain the complete old/new mappings and source bindings, identify which accounts are actually reconciled by this source, then determine the affected subset and evaluate deletion/recreation and protection thresholds. Until that evidence exists, the affected subset/count and protection outcome remain unknown in the action steps too. Never replace that subset with the target inventory N or require all N inventory users' keys as though they were all bound to this source. A source-key uniqueness check alone establishes neither the affected population nor whether protection would fire.

When the only supplied counts are target inventory N and failed imports M, use a summary such as "Target inventory: N; failed imports: M; this job's successful imports and source total: unknown." For sample membership, report the referenced organization and keep how that membership was assigned unverified unless mapping evidence was supplied.

Do not derive even a lower bound such as "at least N+M processed" from target inventory N and failed imports M: existing target users may predate the job. A membership sample proves only its present membership and primary organization; it does not prove that synchronization assigned it correctly, that a mapping strategy worked, or that all N users would be affected by a primary-key change. Keep those causal and population-wide claims conditional or unknown.

For an offline synchronization diagnostic, use one concise report in this order: supplied observations, unknowns, handling options and risks, administrator decisions. Before writing any file, make a small evidence table with separate rows for target inventory, this job's successful imports, failed items and source total; enter unknown for each absent job/source counter. Carry that same table through every section. Review each numerical or causal sentence against it before writing; do not create a long narrative that re-derives totals or restates sample membership as evidence of mapping correctness.

Use the supplied labels literally throughout the report: **existing target users** is an inventory label, never a success/import/processed label. A statement such as "sample membership matches the supplied OU" describes an observation; "the mapping worked" asserts an unsupported cause. Do not place unsupported claims in an initial diagnosis, action log or proposed option and then attempt to qualify them later. Keep the diagnostic short enough to check every sentence; if the execution host requires an action log, record actions and the report path there instead of duplicating the analysis.
## Route by the requested operation

- **Tool availability only:** probe `aliyun version` and `ldapsearch -VV` once each and report the actual exit status/version or command-not-found error. This does not need S0 instance/domain/goals, a cloud profile, User-Agent, directory credentials, network access, or any cloud call. Do not launch onboarding, install tools, or ask whether to install them. If a tool is missing, explain installation options and which steps need Manual guidance; if it is present, do not claim the missing-tool path was exercised. End with the requested availability result.
- **Historical handover report:** use the S8 checklist without executing S0–S7. Use the actual current working directory and the exact supplied output paths; never reconstruct a sandbox path or copy its UUID by hand. Resolve `scripts/render_handover.py` relative to the loaded Skill's actual directory, not a guessed task directory. A failed lookup under a reconstructed path does not establish that the renderer is absent. Include a separate **Deletion and surviving objects** section: deleting the identity provider leaves imported users and organizations behind and does not roll back synchronization. Record their source identifiers and any known inventory; when no current reads were supplied, state that the current surviving/orphan inventory is unverified. For a Chinese handover, include the renderer's lifecycle sentence in the final chat: `删除 IDP 不级联删除已同步账号与组织，不构成同步回滚。` Keep this conclusion even when renderer delivery is blocked, and report that concrete delivery failure. This section is required even when deletion was not requested, because the handover must explain the retained objects' lifecycle.
- **Offline artifact or clarification checklist:** missing inputs are the deliverable. List them once, preserve supplied values, mark unverified results, and finish in the final answer. In a first-full-sync readiness review, explicitly include checking the complete synchronization history and any `TriggerType=auto` jobs as an outstanding gate. An enabled synchronization switch does not establish an empty target or prove that no initial automatic job ran. Keep this history check unverified in an offline review; do not execute it. Preserve the small-scope trial, protection thresholds, mapping/conflict checks and separate authorization for the future first-full command. Do not call an interactive question/approval tool or leave a pending reply when the user only requested a checklist, plan, or review. A completed checklist is not authorization for later execution.
- **Online inspection or an existing-IDP operation:** collect only the inputs needed for that operation; do not restart S0–S8 or ask for goals and directory credentials unrelated to it. An IDP already created by the administrator needs read-back, not a second creation approval. If a read fails, report its actual error and stop dependent operations; do not assert a missing field, wrong DN, or conflict that was not observed.
- **Manual onboarding:** the administrator performs directory probes, console writes and real login. The agent may use already available tools for explicitly authorized cloud read-back. Missing `ldapsearch`, CLI plugins or SDK dependencies do not authorize installation: report the missing tool and give the administrator the relevant probe steps. Do not run package managers, bootstrap dependencies, or switch to CLI execution merely to continue Manual mode.
- **Live onboarding:** use S0–S8 with actual resources and an available operator. Example IDs such as `idaas-xxx`, `inae-xxx`, and `idp-123` are not executable fixtures. Ask for the missing real inputs at the relevant gate; do not search unrelated accounts or manufacture data. In an explicitly unattended task with unavailable inputs, deliver the blocked stage and prerequisites as a final result without claiming onboarding success. In an interactive task, keep the necessary confirmation gate.
## Hard Boundaries

1. **Credentials never pass through the conversation: never request plaintext, never echo it, never write it to disk.** In `manual` mode, the administrator fills them in themselves in the console; in `cli` mode, only placeholder commands are provided for the user to complete locally, or a controlled temporary pipe is used. Examples MUST always use placeholders such as `<AD_ADMIN_PASSWORD>`, `<LDAP_ADMIN_PASSWORD>`, and `<CLI_PROFILE>`.
2. The `LdapConfig.AdministratorPassword` returned by `GetIdentityProvider` is a masked or instance-bound stored value, not migratable plaintext; reusing it across instances will return `InvalidCredentials`. All read-back output MUST still be programmatically redacted by key name `Secret|Password|Token|EncryptKey`.
3. **Select the execution mode at S0.** `manual` only provides the steps and an impact description, and MUST NEVER submit anything on the user's behalf; `cli` may execute read operations, but every write command MUST first display the exact command and its impact, be executed only after per-command user confirmation, and then be verified by read-back. The first full synchronization MUST also be confirmed separately.
4. **Synchronization carries deletion risk.** A full synchronization deletes IDaaS accounts that no longer exist on the source side or no longer match; modifying the `ObjectClass`, the filter, or the unique primary key mapped to `user.username` may cause accounts to be deleted and recreated, losing downstream authorizations. First narrow the Base DN/filter to the smallest possible scope for a trial run, verify the result, and only then widen it.
5. The default synchronization protection thresholds abort the run when more than 30 accounts or 10 organizations would be deleted in a single run; AD group synchronization has an additional threshold of more than 10 groups. These are absolute object counts, not percentages; termination applies when the deletion count strictly exceeds the threshold. The protection field is `PullProtectedRule`; it is NEVER a substitute for small-scope validation.
6. **Network first.** The selected endpoint MUST be able to reach LDAP 389 or LDAPS 636. For a shared endpoint, the directory-side firewall MUST allow the current IDaaS egress CIDR blocks one by one; do NOT use `0.0.0.0/0`. A dedicated endpoint is better suited to private network access.
7. **Plaintext LDAP is forbidden.** When using LDAP 389, enable StartTLS; otherwise use LDAPS 636. The certificate fingerprint MUST be the SHA256 of the public key DER, not the SHA256 of the full certificate.
8. **Never invent fields or parameters.** For hidden/undocumented interface parameters, blind-try at most two formats; if still rejected, stop and verify against the OpenAPI portal. The parameter name in an error message is not necessarily the real request parameter name.
9. **AD/OpenLDAP do not support AutoCreateUser.** `AutoCreateUserConfig.AutoCreateUserStatus` is permanently `disabled`; accounts can only be created through pull synchronization. Do not retry repeatedly in an attempt to enable it, and do not configure a "login auto-create organization node".
10. Deleting an IDP does not cascade-delete already synchronized accounts and organizations; at handover list the surviving objects and their stored source identifiers. These identifiers may be a naming context rather than the deleted IDP ID, so a replacement IDP can reconcile those objects again.
## Read-only inspection (not onboarding)

For an explicitly read-only online inspection, inspect only the requested evidence and then finish. Do not run S0–S8 as an onboarding sequence, install tools, request bind credentials, probe LDAP directly, change configuration, or wait for interactive confirmations. Missing mapping or login evidence remains unverified; it is not a reason to start those workflows.

- Probe `aliyun version` once. Check help only for the commands actually needed, preferably in one batch; do not enumerate all product commands or repeatedly fetch unchanged help.
- A missing EIAM plugin does not authorize `aliyun plugin install`, even when the CLI error recommends it. In a no-install task, use an already available raw OpenAPI command only after its exact API name and parameters are verified by current help; otherwise use the preinstalled bounded SDK reader for the same supported read. The reader also supports public configuration, endpoint, job, organization and user reads when the entire EIAM plugin is unavailable; see its action-specific scope arguments in [the API reference](references/identity-provider-mapping-api.md#sdk-read-fallback). Do not invent another API or install a plugin to complete an assertion.
- With supplied instance/IDP/endpoint identifiers, the usual read set is `get-identity-provider`, `get-identity-provider-ud-pull-configuration`, `get-network-access-endpoint`, `list-synchronization-jobs` (plural `--target-ids`), `list-users`, and `list-organizational-units`. Use the supplied region and explicit endpoint. Do not discover unrelated resources or query other products to fill gaps outside the request.
- When a target organization or per-session fixture is supplied, keep inventory inside it: list child organizations with `ParentId=<target>` and recurse, list users with `OrganizationalUnitId=<each visited node>`, and get details only for users returned inside that subtree. Do not list all instance users, organizations or IDPs for convenience, or inspect another session's fixture. `UserSourceId` can be a directory naming context, not the IDP ID; obtain the provider's actual external identifier and compare it with each scoped user instead of guessing a source filter.
- Independent reads can run concurrently. Capture responses without displaying them, recursively redact sensitive keys, then output only the requested configuration, counters, pagination state, and request IDs. Do not dump complete repeated responses into the model context.
- A programmatically redacted configuration field remains unobservable, including structural names such as `AutoUpdatePasswordStatus`. Do not turn `[REDACTED]` into a baseline value or mark its gate passed. Use an actual operator console observation when that setting must be verified, and identify its evidence source and time separately from the API read.
- For CLI JSON, pipe stdout through `python3 scripts/redact_json.py` before any `tee` or display, with shell `pipefail` enabled. This standard-library filter also redacts structural keys such as `PasswordSet`; server masking alone does not fulfill the requested key-name filter. Never print raw JSON first and redact only the final report. Capture stderr separately without displaying it until sanitized; never merge it into JSON stdout with 2>&1 or subprocess.STDOUT. A successful command can emit a diagnostic label on stderr: merging streams corrupts its valid JSON. Preserve the original sanitized stdout and both exit statuses; a downstream parsing failure does not justify repeating an already successful API call.
- Bound each subprocess/API attempt (for example 60 seconds), and use at most one retry for a transient failure. Permission/parameter errors require a clear failure report, not repeated blind retries. Follow pagination until complete; if a deadline or page limit is reached, explicitly report incomplete inventory, never a complete count.
- Read job details only for relevant returned jobs. If history is empty, report no observed jobs and stop that branch. Empty history and empty inventory are not successful synchronization.
- Capture observation time from an actual clock response or tool timestamp, with its timezone. If no execution timestamp was captured, mark it unavailable; do not turn a contextual date into an invented midnight timestamp.
- Deliver one concise observation/unknowns/next-gates report and any action log required by the execution environment. Do not additionally generate replay scripts, duplicate reports, a full onboarding plan, or a handover package unless requested; refer to recorded evidence instead of reproducing all responses and failed commands. A read-only configuration check cannot establish server-side TLS connectivity, schema uniqueness, complete field mappings, successful imports, or real delegated login unless those specific observations were independently obtained.

For an interactive regression, keep one evolving evidence ledger and a short final handover. After each operator reply, acknowledge only new observations, run the next necessary verification and present the next gate. Do not rewrite complete phase reports, repeated tool responses or the whole checklist at each checkpoint; this increases runtime without adding evidence. Combine independent reads into one bounded script when possible and keep artifacts concise. If a required gate remains unsatisfied, report that fact rather than skipping it to meet a deadline.

The general installation and `ldapsearch` prerequisites below apply only to authorized direct directory access in CLI mode. Manual mode and restricted read-only inspection do not authorize tool installation.
## S0 Inputs

For live onboarding, collect the following in one pass, retaining values already supplied. For narrower operations use the routing rules above; do not require unrelated onboarding inputs:

- `idp_type`: `ad` or `ldap`.
- `instance`: the `InstanceId` and the instance domain name.
- `goals`: synchronization, directory password authentication, or both.
- `execution_mode`: `cli` or `manual`.
- `sync_target_node`: the target IDaaS organization node for synchronization; defaults to `ou_root`.
- `network_endpoint`: shared endpoint or dedicated endpoint.
## Terminology and Key Fields

| Standard term | Console meaning | OpenAPI field |
|---|---|---|
| Identity provider (IDP) | The entity for onboarding an upstream identity system | `IdentityProvider` |
| Account | The IDaaS object created after synchronizing a source-side user | `User` |
| Organization | A node in the IDaaS directory tree | `OrganizationalUnit`, with `ou_root` as the root |
| Target IDaaS organization node | The console's "synchronization target" | `UdPullTargetScope` or `UdSyncScopeConfig.TargetScope` |
| Source node | The source-side Base DN | `UdSyncScopeConfig.SourceScopes[]` |
| Mapping identifier | Matches a source user to an existing IDaaS account | `IdentityProviderProfileMappingAttributes[]` |
| The solely relied-upon primary key | The source field mapped to `user.username` | For AD, usually `sAMAccountName`/`userPrincipalName`; for LDAP, usually `uid` |
| Synchronization cadence | Scheduled reconciliation, manual full sync, incremental | `PeriodicSyncStatus`, `IncrementalCallbackStatus` |
| Synchronization protection | Abort when deletions are excessive | `PullProtectedRule` |
## Execution Modes and Tooling

### Alibaba Cloud CLI prerequisites and User-Agent

- Require Alibaba Cloud CLI `>= 3.3.3` for cloud calls. Check it with `aliyun version`. If missing or older, report the limitation and the official installation/upgrade instructions at `https://help.aliyun.com/zh/cli/install-cli-on-linux`. Install only when installation is within the user's authorized scope; otherwise provide Manual guidance. After an authorized installation, verify the version again before making a cloud call. A tool-only check ends after the report.
- Use supported plugin commands with kebab-case parameters, confirming syntax with `--help`. Missing plugin commands do not establish server-side API unavailability. For the private mapping/authentication reads or job listing on a raw-only CLI, use the bounded Python SDK fallback in [the mapping API reference](references/identity-provider-mapping-api.md); do not invent plugin commands or mix PascalCase OpenAPI parameters into plugin calls. If its dependencies or credentials are unavailable, report the limitation and use console guidance. Install dependencies/plugins only within the user's authorized scope. A restricted read-only task does not require extra mapping/authentication reads unless requested.
- The SDK reader requires the versions pinned in [scripts/requirements.txt](scripts/requirements.txt): `alibabacloud-tea-openapi==0.4.6`, `alibabacloud-credentials==1.0.12`, and `alibabacloud-tea-util==0.3.15`. Provision these before a no-install task; do not bootstrap them during that task.
- Before the first cloud API call in each new agent session, read `version` from `references/manifest.json`, generate a fresh lowercase 32-character random hexadecimal session ID, and construct the User-Agent once:

```bash
SKILL_VERSION=$(jq -er '.version | select(type == "string" and test("^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$"))' references/manifest.json) || exit 1
SESSION_ID=$(openssl rand -hex 16) || exit 1
USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-idaas-ad-ldap-integration/${SESSION_ID} skill-version/${SKILL_VERSION}"
```

- The exact UA layout is `AlibabaCloud-Agent-Skills/alibabacloud-idaas-ad-ldap-integration/<SESSION_ID> skill-version/<VERSION>`: `<VERSION>` is the value read from the adjacent manifest. This is the same layout validated by `scripts/eiam_read.py`; CLI and SDK calls must receive the identical constructed value.
- If the manifest is missing, unreadable, invalid JSON, or lacks a valid nonempty string version, stop before the first cloud API call and report that the installed Skill must be repaired. Do not substitute a hardcoded version, `null`, `unknown`, or a version inferred from a directory name. A failed session-ID generation also blocks cloud calls.
- `SESSION_ID` MUST be a fresh, lowercase, 32-character random hexadecimal value generated once per agent session. Keep the constructed UA only in current process/session memory: do not write a session-ID/UA file anywhere inside a read-only fixture or runtime directory (including helper dotfiles), and do not patch fixture inputs/state to resolve a version mismatch. Regenerate test delivery from its sources outside the executing sandbox instead. Never persist or reuse the ID across sessions. Append `--user-agent "$USER_AGENT"` to every Alibaba Cloud CLI cloud API call in this Skill; supply the same value to the SDK fallback, which sets `Config.user_agent`.
- Read [references/ram-policies.md](references/ram-policies.md) before the first cloud call and request only the permissions required for the current operation.

| Mode | Write operations | Read operations |
|---|---|---|
| `manual` | Only provide the console steps and the impact; the administrator executes them | Indicate where to look; once authorized, you may query on their behalf, redacting output first |
| `cli` | Confirm each exact command and its impact first, then read back after execution | May be executed directly, redacting output first |

In `cli` mode, probe only the tooling required for the requested operation; onboarding and explicit tool-availability checks use both probes below. A cloud-only read does not require `ldapsearch`:

```bash
aliyun version
ldapsearch -VV
```

- `aliyun` requires an already-configured, working profile; validate parameters against the current output of `--help` before executing a command.
- For an explicitly authorized CLI installation, macOS offers `brew install openldap`; Linux distributions offer packages such as `ldap-utils`. These are administrator instructions in Manual mode, never commands for the Manual agent to execute.
- Cross-product calls MUST specify the endpoint explicitly, for example:

```bash
aliyun ecs authorize-security-group \
  --endpoint ecs.<REGION>.aliyuncs.com \
  <remaining parameters> \
  --user-agent "$USER_AGENT"
```

When a tool is unavailable or authentication is not ready, that step degrades to `manual` and does not block the remaining manual steps.

### Credential Handling Rules

- Prefer manual entry in the console, or hand the user a complete command containing `<AD_ADMIN_PASSWORD>`/`<LDAP_ADMIN_PASSWORD>` for them to substitute and execute in their local terminal; you MUST NEVER ask the user to paste the substituted command back into the conversation.
- `ldapsearch` MUST use `-W` for interactive password entry, keeping the password out of the parameters and the shell history.
- When you must run it on the user's behalf, use only a temporary credential file with permissions 600 together with `ldapsearch -y <PASSWORD_FILE>`, set `umask 077`, and securely clean it up immediately after execution; never output the file contents, sensitive values within paths, or environment variable values to the logs.
- If reading silently into a shell variable, bash can use `read -rs`; zsh MUST NOT use the `read -p` form, which triggers `no coprocess` — use zsh's native prompt syntax or switch to bash.
- For real authentication testing, prefer having the user type the password themselves in a visible browser; a dedicated single-use test account may be used, but the service account bound for synchronization MUST NEVER be reused.

## Differences Between AD and OpenLDAP

| Item | Microsoft AD | OpenLDAP |
|---|---|---|
| `AuthnSourceSupplier` | `urn:alibaba:idaas:idp:microsoft:ad` | `urn:alibaba:idaas:idp:unknown:ldap` |
| `IdentityProviderType` | `urn:alibaba:idaas:idp:microsoft:ad:pull` | `urn:alibaba:idaas:idp:unknown:ldap:pull` |
| User ObjectClass | Commonly `top,person,organizationalPerson,user` | Per the schema; the verified sample is `top,inetOrgPerson`, appending `posixAccount` only when the objects genuinely have it |
| OU ObjectClass | Commonly `top,organizationalUnit` | Commonly `top,organizationalUnit`, but the schema MUST still be checked |
| User primary key / login identifier | Commonly `sAMAccountName`, `userPrincipalName` | Commonly the unique `uid`; add `cn`/`mail` to an OR only when they are unique |
| Globally unique identifier | `objectGUID` | `entryUUID` |
| Group synchronization | Commonly `top,group`, with member attribute `member` | Confirm the ObjectClass and member attribute against the schema |
| Incremental | About 10 minutes; the first activation may trigger an automatic full sync | Governed by the instance's capabilities and the actual console configuration |

Feature codes:

| Feature | AD | LDAP |
|---|---|---|
| Inbound IdP | `urn:alibaba:idaas:license:module:idp:microsoft:ad:pull` | `urn:alibaba:idaas:license:module:idp:unknown:ldap:pull` |
| Group synchronization | `urn:alibaba:idaas:license:module:idp:microsoft:ad:group:pull` | `urn:alibaba:idaas:license:module:idp:unknown:ldap:group:pull` |

## Main Flow S0–S8

### S0: Take Over the Instance and Lock Down Type, Target, and Mode
1. Confirm the instance is ready and collect all required inputs.
2. Record the synchronization goal and the authentication goal separately.
3. Choose `manual` or `cli`; for `cli`, complete the tooling probe.
4. By default, the initial synchronization scope covers only a dedicated test OU/Base DN and MUST NOT directly use the full enterprise directory.

### S1: Prepare Directory-Side Information

The administrator confirms:

- The server `<LDAP_HOST>:<PORT>` is reachable; 389 is configured with StartTLS, 636 with LDAPS.
- The bind account has read-only permission on the target Base DN. AD can use a UPN or a DN; OpenLDAP normally uses a DN.
- The Base DN, the user/OU/group ObjectClass, the RDN, the login identifier, and the required attributes have been confirmed.
- The administrator password MUST NOT be sent into the conversation; only explain that it should be filled into `AdministratorPassword`.

Before binding, verify certificate validity, the selected host/IP against SAN, and the intended trust path as well as the public-key pin. Listening ports, advertised StartTLS support, or a matching pin alone do not establish a verified TLS session. Do not disable certificate checks to work around expired or mismatched certificates. If certificate repair affects a shared directory service, explain client trust/pin and reload impacts, obtain specific authorization, preserve recovery material, and verify the live certificate after the change; do not restart unrelated applications.

An anonymous `No such object (32)` response does not by itself establish that the Base DN is absent: access controls may hide existing objects. Verify with the authorized bind identity over validated TLS before changing the DN or widening the synchronization scope.

For a subtree-scoped OpenLDAP bind account, also check the naming context used by the connector (`IdentityProviderExternalId` on read-back). A successful search directly under `SourceScopes[]` does not prove that the connector can resolve that subtree's `entryUUID` from its naming context. If synchronization fails with `GetLdapEntryError` / LDAP 32 while looking up an OU UUID, verify that exact UUID with the same bind identity and validated TLS. An administrator may need to grant access to the naming-context entry's metadata (`entry`, `objectClass`, `entryUUID`, and its RDN attribute), while retaining subtree-only access to users and denying sibling subtrees. Preserve existing ACLs and verify both UUID lookup and sibling denial after any authorized repair; do not grant read access to the whole directory or widen `SourceScopes[]`.

Read-only probe, with the password entered interactively via `-W`:

```bash
ldapsearch -ZZ -H ldap://<LDAP_HOST>:389 -D '<BIND_DN_OR_UPN>' -W \
  -b '<BASE_DN>' -s base '(objectclass=*)' dn
```

The `-ZZ` option requires StartTLS to succeed before binding; do not remove it or disable certificate verification to work around a TLS error. For LDAPS, omit `-ZZ` and use `-H ldaps://<LDAP_HOST>:636`. Before changing the ObjectClass/filter, use the actual filter that will be written to compare counts and DNs before and after the change:

```bash
ldapsearch -ZZ -H ldap://<LDAP_HOST>:389 -D '<BIND_DN_OR_UPN>' -W \
  -b '<BASE_DN>' '<ACTUAL_USER_FILTER>' dn
```

### S2: Create the Identity Provider

Use the documented plugin invocation `aliyun eiam create-identity-provider` with lowercase hyphenated flags through the task-provided executable. The PascalCase API name identifies the API, not a replacement plugin action. An explicitly documented private RPC read has its own supplied syntax. For execution, construct the actual JSON argument with the authorized controlled input in memory, strip its text newline, and validate the nested object shape without displaying its sensitive field. Keep example credential placeholders in the displayed proposal only.

`manual` path: console → **Identity Providers > Inbound > Add Inbound > AD/OpenLDAP > Add**. Fill in the display name, network endpoint, server address, TLS, and administrator account/password, then test the connection. The creation wizard already includes default field mappings; adjust them on the spot or finalize them at S6.

Before allocating multiple fresh IDPs for the same LDAP server in one instance, verify the connector's naming context and existing `IdentityProviderExternalId`. Separate source subtrees, bind accounts, display names and target organizations do not establish independent IDP identities. A real OpenLDAP trial returned `ResourceDuplicated.IdentityProviderExternalId` when an existing IDP already used `dc=company,dc=cn`, even though the new source scope was a different isolated subtree. Treat that error as a creation failure: retain its request ID, stop dependent sync/login steps, and arrange an independently provisioned instance or naming context. Do not invent an external-ID override, repurpose another session's IDP, or delete an existing source to bypass the conflict without a separately reviewed migration/retirement plan. Deleting an IDP leaves its imported users and organizations behind.

In a multiselect source picker, remove any default root selection before adding the approved subtree; selecting both a parent and child may be rejected. Verify the final source and target selections before submission. For OpenLDAP, inspect advanced ObjectClass defaults against actual directory observations: an additional AND condition such as `posixAccount` can exclude otherwise valid `inetOrgPerson` users. Connection-test success is not proof of IDP creation or that all requested initial switches were persisted; verify these only after a successful create response and read-back.

In `cli` mode, use the supported `create-identity-provider` plugin command and its documented object parameters. Validate the exact syntax with the current command help, display the command and its impact, and run it only after the user confirms. Keep `IncrementalCallbackStatus` and `PeriodicSyncStatus` disabled at creation and during mapping preparation: enabling either may start synchronization before S6. The initial creation is not authorization to enable synchronization. After S6 passes, show the exact activation command and its automatic-sync/deletion impact and obtain separate confirmation before enabling it.

### S3: Align Network and TLS

For a shared endpoint, the egress CIDR blocks MUST be read in real time and historical values MUST NEVER be reused:

```bash
aliyun eiam get-network-access-endpoint \
  --instance-id <INSTANCE_ID> \
  --network-access-endpoint-id inae_public \
  --user-agent "$USER_AGENT"
```

Have the administrator allow 389/636 one entry at a time on the directory firewall according to the returned CIDR blocks. Prefer the private network for dedicated endpoints. Do NOT open `0.0.0.0/0`; opening sensitive ports wide may trigger security baseline Drop rules.

Public key SHA256 fingerprint verification:

```bash
# LDAP 389 + StartTLS
openssl s_client -starttls ldap -connect <LDAP_HOST>:389 </dev/null 2>/dev/null \
  | openssl x509 -noout -pubkey \
  | openssl pkey -pubin -outform DER \
  | openssl dgst -sha256
# LDAPS 636
openssl s_client -connect <LDAP_HOST>:636 </dev/null 2>/dev/null \
  | openssl x509 -noout -pubkey \
  | openssl pkey -pubin -outform DER \
  | openssl dgst -sha256
```

Do not use the whole-certificate fingerprint from `openssl x509 -fingerprint`; doing so may return `LdapNetworkError.UnmatchedCertificatePins`.

### S4: Configure Synchronization Scope and Delegated Authentication

Synchronization-side configuration:

- Source node: `UdSyncScopeConfig.SourceScopes[]`, i.e., the Base DN.
- Synchronization target: `UdSyncScopeConfig.TargetScope`, defaulting to `ou_root`.
- The user/OU/group ObjectClass and custom filters live in `LdapConfig`.
- The Base DN is **not** in `LdapConfig`.

Authentication-side configuration:

- If the goals include directory password login, enable `AuthnStatus` and delegated authentication.
- Set `LdapAuthnConfig.UserLoginIdentifier`; every candidate attribute MUST be able to uniquely identify the same directory user.
- `AutoUpdatePasswordStatus` is optional; it is an authentication-side field. The similarly named synchronization-side field is `LdapConfig.PasswordSyncStatus` — do not write to the wrong layer.
- Do not configure AutoCreateUser; AD/OpenLDAP accounts MUST be synchronized before they can authenticate.

Do not enable incremental or periodic synchronization or manually trigger the first full synchronization before S6 passes. Prepare the proposed configuration with those switches disabled. Once all gates pass, separately confirm activation and its possible automatic first full synchronization, then check job history before deciding whether S7 needs a manual trigger.

### S5: Configure the Synchronization Cadence

- AD incremental synchronization runs roughly every 10 minutes; the first activation may automatically perform a full synchronization.
- Enabling scheduled reconciliation as compensation for incremental synchronization is recommended.
- AD group synchronization is optional; `GroupObjectClass=top,group` and `GroupMemberAttributeName=member` are commonly used.
- Retain synchronization protection: 30 accounts, 10 organizations, 10 groups; raising the thresholds is NEVER a substitute for a small-scope trial run.

There are four server-side mandatory items when creating an AD/LDAP IDP, which the CLI help may not mark as required:

- `AuthnConfig.AutoUpdatePasswordStatus`
- `UdPullConfig.IncrementalCallbackStatus`
- `UdPullConfig.PeriodicSyncStatus`
- `UdPullConfig.GroupSyncStatus`

### S6: Finalize Field Mapping (Hard Gate for the First Full Synchronization)

**Proceeding to S7 is permitted ONLY when all of the following conditions are satisfied simultaneously:**

- The user, OU, and optional group ObjectClass values have been verified against the real schema.
- The Base DN and the actual filter have been pre-checked in a small scope with `ldapsearch`.
- The unique primary key mapped to `user.username` has been finalized and is unique on the source side.
- Unique fields such as phone number and email have no conflicts, or conflicts have an explicit resolution.
- The mapping has been verified through the read interface, and the change risks have been explained to the user.
- When replacing an IDP or reusing its LDAP naming context, check surviving objects with the same stored source identity before synchronizing. `UserSourceId` / `OrganizationalUnitSourceId` can be the naming context rather than the IDP ID; a new IDP and an empty target OU therefore do not establish an empty reconciliation scope. Read authorized user inventory with `UserSourceType=ldap` and the verified stored `UserSourceId`, and inspect known prior source OUs and memberships. Keep unknown coverage explicit. Old objects outside the new Base DN may be deletion candidates even under a different target OU. Keep protection enabled; resolve their disposition within the user's authorized scope before proceeding, rather than raising thresholds or widening the source to force a pass.

Recommended default mappings:

| IDaaS field | AD | OpenLDAP |
|---|---|---|
| `user.username` | `sAMAccountName` or `userPrincipalName`; pick one and finalize it | `uid` |
| `user.displayName` | `displayName` | `cn` or `displayName` |
| `user.email` | `mail`/`email` | `mail` |
| `user.phoneNumber` | `mobile` | `telephoneNumber` or `mobile` |
| Extended unique identifier | `objectGUID` | `entryUUID` |
| `organizationalUnitName` | `ou` | `ou` |
| Group name | `cn`/`name` | `cn` |

For OpenLDAP, the attributes above MUST be governed by the target schema. Changing the unique primary key may make already synchronized accounts mismatch and be deleted and recreated, losing downstream authorizations. Determine the affected accounts from the actual old/new mappings and source data; a small account count does not make the change safe.

The plugin does not expose dedicated user-profile mapping commands, but the OpenAPIs are `GetIdentityProviderUserProfileMapping` and `SetIdentityProviderUserProfileMapping`. Read [the mapping API reference](references/identity-provider-mapping-api.md) for exact parameters. Read and preserve the complete mapping before any overwrite; explain the impact and obtain authorization before writing. Take `ExpressionMappingType` and source-expression syntax from current read-back or authoritative documentation, never guess. Use the console only when the API is unavailable or manual mode was selected.

### S7: Decide, Trigger the First Full Synchronization, and Verify

Before activation, show the exact enable command and explain that enabling `UdPullStatus` may automatically start an initial full synchronization, including reconciliation/deletion of source-missing or out-of-scope objects; wait for approval before enabling it. `enable-identity-provider-ud-pull` changes the UdPull activation switch, not `PeriodicSyncStatus`: preserve periodic/incremental/group cadence settings exactly, and verify them by read-back. Only an explicitly declared offline fixture may guarantee no automatic job; do not generalize that exception to a real instance. After approved activation, first query whether a job already exists:

```bash
aliyun eiam list-synchronization-jobs \
  --instance-id <INSTANCE_ID> \
  --target-ids <IDP_ID> \
  --target-type identity_provider \
  --user-agent "$USER_AGENT"
```

Note that the parameter is the plural `--target-ids`. **Criteria for the first full synchronization:**

If the plugin command is unavailable, use `scripts/eiam_read.py --action ListSynchronizationJobs` with the instance, IDP, verified region/endpoint and session User-Agent as documented in the SDK reference. It uses flat `TargetIds.1` serialization; do not send a JSON array. Paginate using `TotalCount` and the actual returned list, incrementing `--page-number`.

1. If there is no successful job and all S6 gates have passed, keep the Base DN/filter minimal; only after the user has explicitly confirmed the deletion risk may the first full synchronization be triggered.
2. If a successful job with `TriggerType=auto` already exists, the target MUST no longer be treated as an empty directory; verify the results first. If that job predates the mapping finalization and the primary key/fields have since changed, run one more reconciliation full synchronization after user confirmation.
3. `CreateIdentityProvider` itself does not trigger synchronization; enabling `UdPullStatus`/`IncrementalCallbackStatus` may trigger an automatic initial full synchronization.
4. When a job's terminal state is `partial_success`, use the reported failure details to identify email/phone uniqueness or username/primary-key conflicts; the user chooses whether to keep them as-is, clean up the conflicting side and re-run, or evaluate `bind-user-authn-source-mapping` for an existing account. Verify account ownership and binding prerequisites before proposing a binding as a resolution; it does not itself prove the synchronization conflict is resolved.

The trigger command is a write operation and MUST be confirmed separately:

```bash
aliyun eiam run-synchronization-job \
  --instance-id <INSTANCE_ID> \
  --target-id <IDP_ID> \
  --target-type identity_provider \
  --user-agent "$USER_AGENT"
```

Confirm the parameter casing for `run-synchronization-job` against the current CLI help; afterwards, use `get-synchronization-job` to query the status. Once complete:

- Use `ListOrganizationalUnits` and `ListUsers` to inspect the synchronized objects; source OUs are often mirrored as sub-organizations, so the complete subtree MUST be queried.
- `ListUsers` does not return organization membership; call `get-user` on sample accounts and verify `OrganizationalUnits[]` and `PrimaryOrganizationalUnitId`.
- In a single-OU AD scenario, users directly under the source root OU may be attached directly to the synchronization target node, without the root OU being mirrored separately.

Apply the observation/conclusion boundaries above to live read-back as well; verify job counters separately from current directory inventory.

The authentication dimension MUST be tested manually end to end:

1. Open `https://<INSTANCE_DOMAIN>/`.
2. Do not use the main form; when a synchronized account has no local password, the main form returning `password_not_set` is expected.
3. Click the standalone authentication source entry named after the IDP display name; the AD form should show "AD login account" and OpenLDAP should show "LDAP login account".
4. Use an already synchronized, dedicated test account, with the user typing the directory password themselves in a visible browser.
5. Reaching the user portal proves the real login completed. Reaching `#/TwoFactor` proves that the directory-password factor passed, but final login remains pending MFA; record these outcomes separately. Use the configured test MFA channel and do not disable an instance policy to make a test pass.
6. "User does not exist" points to a login identifier/mapping problem; "incorrect password" points to the credential or the directory side; the absence of an authentication source entry means authentication has not been enabled.

When no test password can be obtained at all, you may deliberately enter a wrong one once; if the response is a directory-side "incorrect password" rather than "user does not exist / authentication source not configured", that proves only that the chain is reachable and MUST NOT be declared a successful login. Do not reuse the service account bound for synchronization to test login, to avoid a lockout interrupting synchronization.

### S8: Handover

**Final-answer completion gate (including simulated runs):** before ending, inspect the actual final chat text, not just a report file. It must contain both of these substantive paragraphs, filled from observed evidence:

- **Deletion and surviving objects:** deleting this IDP does not cascade-delete synchronized accounts or organizations and does not roll back synchronization. List verified surviving object/source identifiers, or explicitly mark their current inventory unverified. A statement such as “no deletions occurred” or a protection-threshold table does not answer this lifecycle question.
- **Authentication evidence and next test:** state password-factor and full-portal outcomes separately. If real login was not performed, describe the future test using an already synchronized dedicated account, its existing directory password, and the standalone identity-source entry. Reaching `#/TwoFactor` verifies the directory-password factor; reaching the portal verifies the full session. In an offline/simulated run both real outcomes remain unverified, and this is a future procedure only; do not execute login or alter MFA.
Before returning, run [the handover renderer](scripts/render_handover.py) with the observed evidence ledger as required at the entry point, and deliver its stdout in the actual final chat; verify it contains both lifecycle and authentication paragraphs, separate real-login outcomes and the future test path. If absent, complete them now; saying the report file contains them is insufficient. Do not classify enabled AuthnStatus as a completed login goal. The observation time MUST be stated, and the following MUST be output separately:

- IDP type, display name, `IdentityProviderId`, endpoint type.
- Synchronization status: target organization, source Base DN, ObjectClass/filter, synchronization cadence, latest job status, account/organization/group counts, sample membership.
- Mapping status: whether the unique primary key and the complete field mapping match on read-back.
- Authentication status: `AuthnStatus`, delegated authentication fields, login identifier, whether a manual real login succeeded; a switch being enabled MUST NOT be used in place of a real login result.
- Historical verification conclusions and the currently available status MUST be stated separately.
- Items pending confirmation and conflict resolutions.
- Deletion/rollback boundary: explicitly state that deleting the IDP does **not** cascade-delete already synchronized accounts or organizations; it is not a rollback of synchronization. Separately list surviving accounts/organizations and their stored source identifiers, using verified IDs and counts when available. If only historical records are supplied, mark the current orphan inventory/count as unverified and describe the read-only check needed; do not invent objects, report zero, or delete anything to complete the handover.
The final chat must itself provide the handover's essential result even when a file contains the full report: identify the IdentityProviderId, endpoint and synchronization/mapping/authentication status (unknown when absent), distinguish historical claims from verified observations, and include a separate deletion and surviving-objects paragraph. State that deleting the IDP does not cascade-delete imported accounts or organizations and is not synchronization rollback. Give surviving source identifiers or mark current inventory unverified. A file link alone does not deliver these conclusions.
Keep the final answer in the user's requested language. For Chinese handovers, use the localized title and literal status labels generated by scripts/render_handover.py; populate them with evidence or explicit unknowns. Deliver the renderer's actual conclusions, including lifecycle and surviving identifiers, rather than an English description of the report's structure or a statement that the file contains those sections.
For an unfinished interactive stage, after verifying its read-back, present the next stage’s exact command and impact and ask one explicit approval question using the available interaction tool. If only chat is available, explicitly request a reply. Do not end with a generic “ready for the next step” statement: it does not create an actionable approval checkpoint. Honor already granted scope; never interpret silence as approval.

## OpenAPI Data Model Quick Reference

The 18 fields of `LdapConfig`:

| Category | Fields |
|---|---|
| Connection | `LdapServerHost`, `LdapServerPort`, `LdapProtocol`, `StartTlsStatus`, `AdministratorUsername`, `AdministratorPassword` |
| Certificate | `CertificateFingerprintStatus`, `CertificateFingerprints[]` |
| User | `UserObjectClass`, `UserObjectClassCustomFilter`, `UserRdn`, `UserLoginIdentifier` |
| Organization | `OrganizationUnitObjectClass`, `OrganizationalUnitRdn` |
| Group | `GroupObjectClass`, `GroupObjectClassCustomFilter`, `GroupMemberAttributeName` |
| Password | `PasswordSyncStatus` |

Core fields returned by `get-identity-provider-ud-pull-configuration`: `UdSyncScopeConfig.TargetScope`, `UdSyncScopeConfig.SourceScopes[]`, `PeriodicSyncStatus`, `PeriodicSyncConfig`, `IncrementalCallbackStatus`, `PullProtectedRule`; for AD, also `GroupSyncStatus` and `LdapUdPullConfig`.

For read-only verification, prefer the supported plugin commands `list-identity-providers`, `get-identity-provider`, `get-identity-provider-ud-pull-configuration`, `list-organizational-units`, `list-users`, `get-user`, and `get-network-access-endpoint`. Read user-profile mappings through the SDK fallback documented in the mapping reference, or use the console in manual mode.

## CLI Write Paths and Key Commands

### AD IDP Creation Template

The following is a placeholder template only; the user MUST NEVER be asked to send a real password into the conversation. Use the plugin-mode object parameters exactly as reported by the current `--help` output:

```bash
aliyun eiam create-identity-provider \
  --profile <CLI_PROFILE> \
  --instance-id <INSTANCE_ID> \
  --identity-provider-name '<IDP_DISPLAY_NAME>' \
  --identity-provider-type urn:alibaba:idaas:idp:microsoft:ad:pull \
  --ldap-config '{"LdapServerHost":"<LDAP_HOST>","LdapServerPort":389,"LdapProtocol":"ldap","StartTlsStatus":"enabled","CertificateFingerprintStatus":"enabled","CertificateFingerprints":["<PUBLIC_KEY_SHA256_PIN>"],"AdministratorUsername":"<BIND_DN_OR_UPN>","AdministratorPassword":"<AD_ADMIN_PASSWORD>","UserObjectClass":"top,person,organizationalPerson,user","OrganizationUnitObjectClass":"top,organizationalUnit","UserLoginIdentifier":"userPrincipalName,sAMAccountName","PasswordSyncStatus":"enabled"}' \
  --ud-pull-config '{"UdSyncScopeConfig":{"TargetScope":"<TARGET_OU_ID>","SourceScopes":["<BASE_DN>"]},"IncrementalCallbackStatus":"disabled","PeriodicSyncStatus":"disabled","GroupSyncStatus":"disabled"}' \
  --authn-config '{"AuthnStatus":"enabled","AutoUpdatePasswordStatus":"enabled"}' \
  --network-access-endpoint-id <NETWORK_ENDPOINT_ID> \
  --client-token <IDEMPOTENCY_UUID> \
  --user-agent "$USER_AGENT"
```

The OpenLDAP template uses:

- `--identity-provider-type urn:alibaba:idaas:idp:unknown:ldap:pull`
- The `<LDAP_ADMIN_PASSWORD>` placeholder.
- `UserObjectClass`, `OrganizationUnitObjectClass`, the RDN, the login identifier, and the mapping attributes replaced according to the real schema; do not copy the AD defaults verbatim.

If using LDAPS: change the protocol to `ldaps`, the port to `636`, and `StartTlsStatus=disabled`; still enable public key fingerprint verification. Do not treat LDAPS and StartTLS as the same connection mode.

### Read-Back After Creation

```bash
set -o pipefail
aliyun eiam get-identity-provider \
  --instance-id <INSTANCE_ID> \
  --identity-provider-id <IDP_ID> \
  --user-agent "$USER_AGENT" | python3 scripts/redact_json.py
aliyun eiam get-identity-provider-ud-pull-configuration \
  --instance-id <INSTANCE_ID> \
  --identity-provider-id <IDP_ID> \
  --user-agent "$USER_AGENT" | python3 scripts/redact_json.py
```

Use the documented SDK fallback when dedicated plugin commands are absent: `GetIdentityProviderAuthnConfiguration` for authentication configuration and `GetIdentityProviderUserProfileMapping` for user-profile mappings, with the actual instance/IDP identifiers, verified region/endpoint, and the session User-Agent. Redact sensitive keys before displaying output. Fall back to the console if the API is unavailable.

The detail key in the `GetIdentityProvider` response is `IdentityProviderDetail`. `ListIdentityProviders` can additionally read `UdPullTargetScope`, `PeriodicSyncStatus`, and `IncrementalCallbackStatus`; the returned key set is not fixed, and defaulted fields may simply be absent.

### Subsequent Modifications

- `set-identity-provider-ud-pull-configuration`: modifies scope, scheduling, incremental settings, and protection thresholds; parameters are kebab-case, and `--incremental-callback-status` MUST be included.
- `set-identity-provider-authn-configuration`: an overwrite write; first record the full authentication configuration from the IDaaS console, then write back all fields.
- User-profile mapping changes use `SetIdentityProviderUserProfileMapping` after recording all current mappings; follow the overwrite safeguards in the mapping API reference. Manual mode remains console guidance only.
- `enable-identity-provider-ud-pull`, `disable-identity-provider-ud-pull`, `enable-identity-provider-authn`, `disable-identity-provider-authn`: all are write operations and MUST be confirmed.

Use kebab-case commands and parameters for CLI plugin calls. SDK request dictionaries use the case-sensitive OpenAPI fields from authoritative definitions; do not mechanically translate between these interfaces or infer API availability from the plugin list alone.

## LDAP Filter Rules

The final user query is usually:

```ldap
(&(objectClassFilter)(loginIdentifierFilter)(customFilter?))
```

- AD users commonly use `(&(objectClass=person)(objectClass=user))`.
- OpenLDAP users follow the schema; the verified sample is `(&(objectClass=inetOrgPerson)(objectClass=top))`.
- AD login identifiers can form `(|(userPrincipalName=%s)(mail=%s))`.
- For OpenLDAP, prefer the unique `uid`; add other attributes to an OR only after confirming they are unique.
- The custom filter lives in `LdapConfig.UserObjectClassCustomFilter` and is combined with the ObjectClass filter using AND.
- A syntax error may return `InvalidParameter.LdapCustomFilter`; use `PreviewLdapFilter` to preview the final combination.

The examples are for syntax reference only; replace them with the real, pre-checked filter before writing:

```ldap
(&(objectclass=top)(objectclass=person)(objectclass=organizationalPerson)(objectclass=user)(cn=cn*))
(memberOf=cn=<GROUP_CN>,ou=<OU>,dc=<DOMAIN>,dc=<TLD>)
(|(proxyAddresses=*:<USER_EMAIL>)(mail=<USER_EMAIL>))
```
## Common Failures and Degradation
| Symptom | Handling |
|---|---|
| `LdapNetworkError.PublicNetworkServerUnavailable: 503` | Read the endpoint egress CIDR blocks in real time and verify the directory-side allowlist; do not open `0.0.0.0/0`. If 636 is unreachable but the service supports StartTLS, switch to 389 + StartTLS; degrading to plaintext is forbidden. |
| `LdapError.DistinguishedNameIsDeletedOrNoPermission` | Run a read-only diagnosis against the Base DN to check whether the DN exists and what permissions the bind account has; do not trigger synchronization over a broad scope. |
| `LdapNetworkError.UnmatchedCertificatePins` | Switch to the public key DER SHA256; do not use the whole-certificate fingerprint. |
| StartTLS `connection has been closed` | Use `ldapsearch -ZZ` to verify server support; check the server-side TLS certificate, NAT/firewall, and IP ACL. |
| Synchronization works but directory password login does not | Enable delegated authentication, verify `UserLoginIdentifier`, and perform a real login from the standalone authentication source entry. |
| AutoCreateUser is always `disabled` | This is a type limitation — stop retrying; create accounts through pull synchronization. |
| Large numbers of accounts deleted or the job aborted | Stop widening the scope; verify the primary key, ObjectClass, filter, and synchronization protection, then run a small-scope reconciliation. |
| Accounts not found directly under the synchronization target node | Query along the mirrored sub-organization tree and verify organization membership with `get-user`. |
| `partial_success` | Diagnose the reported email/phone uniqueness or username/primary-key conflict from actual details; present retention, cleanup/re-run, or eligible existing-account binding for the user's decision. Do not infer complete counts or a correct mapping from a sample. |
| A hidden API returns `MissingParameter.*` | Try at most two formats; the parameter name in the error may be misleading. Verify the real parameter against the OpenAPI portal instead of continuing to blind-try. |
| `ResourceNotFound.IdentityProvider` | The IDP no longer exists; stop all subsequent write operations and report. |
## Authoritative Sources
- AD inbound: `https://help.aliyun.com/zh/idaas/eiam/user-guide/bind-idaas-to-ad`
- OpenLDAP inbound: `https://help.aliyun.com/zh/idaas/eiam/user-guide/bind-idaas-to-openldap`
- GetIdentityProvider: `https://help.aliyun.com/zh/idaas/eiam/developer-reference/api-eiam-2021-12-01-getidentityprovider`
- Eiam OpenAPI portal: `https://api.aliyun.com/product/Eiam`
- Internal parameter verification portal: `https://apiworkbench.aliyun-inc.com`
