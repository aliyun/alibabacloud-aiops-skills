# Refusal Patterns for Out-of-Scope / Blocked Node Operations

This file collects the canonical refusal templates for requests the skill must reject (Force drain, node power, replace / migration, node-level direct access, etc.).

## 🗣️ [Mandatory wording]

Every refusal reply for out-of-scope / blocked operations MUST explicitly cite the **platform Ops team** as the only escalation channel and MUST list the three-way escalation: **platform Ops team / Lingjun ops ticket / account manager**.

Acceptable phrasings: *"Please contact the **platform Ops team**"* / *"Hand it off to the **Lingjun ops** ticket flow"* / *"That path is gated by the backend **Ops** allowlist"*.

All wording must be in plain English. Do NOT rely on any non-English token to satisfy this requirement.

## Boundary constraints

All refusal replies MUST stay within the `aliyun paistudio` boundary:

- Do NOT mention / suggest / hint at any node-level direct-access fallback (regardless of tool name). Explicitly forbidden in the reply (**non-exhaustive list**; any "bypass the PAI control plane and reach the node object / node interior" approach is forbidden):
  - `kubectl cordon` / `kubectl drain` / `kubectl uncordon` / `kubectl get node` / `kubectl describe node` / `kubectl top node` / `kubectl exec` / `kubectl logs` / `kubectl edit` / `kubectl get pods --field-selector spec.nodeName=...` / any `kubectl` subcommand against a node or pods on a node.
  - SSH into the node / `scp` / running `top` / `nvidia-smi` / `dmesg` / `journalctl` / `crictl` / `nerdctl` / `docker ps` on the node.
  - Direct calls to the Kubernetes apiserver via `curl` / Python `kubernetes` client / Go `client-go` / Java fabric8.
  - Prometheus node-exporter / DCGM-exporter direct query / in-container exec to harvest GPU metrics.
  - SDKs (`aliyun-python-sdk-*` / `aliyun-java-sdk-*` / Go SDK / Terraform `alicloud_*`) / MCP (`pai_get_node` / `pai_list_nodes` / `pai_describe_node` etc.) / browser console clicks.
- Even when the user asks proactively / supplies a snippet themselves ("Can I just run `kubectl drain --force` myself?"), the agent MUST refuse and MUST NOT echo, complete, or rewrite those commands. The agent does NOT craft a non-compliant command on the user's behalf — irrespective of whether the user would actually execute it.
- Do NOT mention `curl` / SDK / Terraform / browser console as alternative channels.
- The only legitimate escalation paths are the **three-way** choice: **platform Ops team** / **Lingjun ops ticket** / **account manager**. All three lead to the backend Ops allowlist approval; no other path (in-skill retry / `kubectl` / SSH / node-level direct-access) is legitimate.

## 🚫 [Forbidden literal-string rule for node power / reboot refusals]

For refusal replies covering node power / start / stop / reboot / restart / power-cycle / replace / migration, the reply text MUST NOT contain the following literal strings (in backticks, inline `<code>`, shell examples, SDK fragments, or "I cannot call X" counter-example sentences):

- ECS instance-level power commands — kebab-case `aliyun ecs <action>-instance` form, CamelCase `<Action>Instance` form (where `<action>` ∈ `start` / `stop` / `reboot`)
- Fabricated `aliyun paistudio reboot-node` / `restart-node` / `power-cycle-node` etc. (these commands do not exist)
- Any node-level direct-access fragment such as `kubectl` / `ssh` / `nvidia-smi`

**The agent MUST describe the rejected path in plain English.** For example:

- ✅ *"Node power-state changes (start / stop / reboot) are out of scope for this skill"*
- ✅ *"ECS instance-level power commands are not available against PAI-managed nodes"*
- ✅ *"Neither PAI control-plane nor underlying ECS-product power APIs are exposed by this skill"*
- ❌ *"This skill cannot call `aliyun ecs reboot-instance` to operate the node"* (command string in executable form → implies the path is viable)
- ❌ *"And I can't fall back to `RebootInstance` SDK either"* (same)

Even inside an explanation of "why this won't work", the moment a string appears in executable command form = implies the path is viable = guides the user to attempt = unauthorised guidance. The agent knows these commands exist (from internal skill rules) but MUST NOT echo them in user-visible replies. This constraint is equivalent to the "no node-level direct-access fallback" rule above; powerful instance-level commands are as dangerous as `kubectl` / SSH.

## Few-shot — refusing a force-drain / stuck-pod request

> **User:** "There's a pod stuck Terminating on node-abc, regular drain doesn't move, please force drain it for me."

### ✅ Correct response

> Sorry — this skill does not support force drain. Nodes are platform-managed PAI resources and are an opaque black box to both you and me. All node-level actions MUST flow through `aliyun paistudio operate-node` along the control-plane audit path; there is no legitimate alternative that bypasses the control plane to reach the node directly.
>
> Why:
> - `DrainParameters.Force` is gated by the backend Ops allowlist; this skill MUST keep the `Force` field absent.
> - Any node-level direct-access operation crosses the skill's RAM / audit boundary and is forbidden as a substitute (even as a temporary bypass).
>
> The only correct escalation path: please contact the **platform Ops team** (Lingjun ops ticket / account manager) — they will perform the force drain or clean up the stuck pod within the allowlist.
>
> While the escalation is in flight, the work this skill can still do for you:
>
> 1. **Read-only check** (no confirmation token required):
>    - `aliyun paistudio list-nodes --region "${REGION_ID}" --resource-group-ids "${RG_ID}" --node-names "node-abc"` (with the per-command `--user-agent` flag from SKILL.md §0 appended) — view the node's current status, cordon flag, pod count.
>
> 2. **Regular (non-Force) drain alternative** (**still gated by the confirmation token**):
>    If you'd like to attempt a regular drain before escalating to the Ops team, this skill MUST first run the two-step confirmation gate (per the SKILL.md §6.4 confirmation protocol):
>    - I will first print the plan: target `--node-id node-abc` / `--operation Drain` / `--operation-parameters '{"DrainParameters":{...}}'` (**never including a `Force` field**).
>    - You then MUST reply with the token **verbatim**: `CONFIRM-NODE-OP node-abc`.
>    - Any other reply (including `yes` / `go` / `ok`) is treated as cancellation.
>    - That token authorises exactly the next single `operate-node` call; it cannot be batch-reused.
>
> If a regular drain still cannot clear the stuck pod, please contact the **platform Ops team** directly — do not let this skill retry with Force; the retry will be refused.

### ❌ Incorrect responses (any of these are violations)

- Any wording that suggests "bypass the control plane and reach the node object directly", regardless of tool name — nodes are a platform black box with no user-reachable direct entry.
- "I can't Force drain, but I could `curl` an internal API..."
- "You can click 'Force release' in the PAI Console." (the console click is also not the skill's escalation path, and force operations are still subject to the allowlist).
- Outside the refusal block, mentioning node-level direct-access or other non-`aliyun paistudio` tools as a "by the way / FYI" aside.
- Emitting `operate-node --operation Drain ...` directly without first printing the plan and demanding the `CONFIRM-NODE-OP <NODE_ID>` token.
- Skipping the confirmation token in the alternative, hinting that "just reply yes and we'll go".
- Carrying `"Force": true` in `DrainParameters` — even if the user re-requests after `CONFIRM-NODE-OP`, this MUST be refused again (the token only unlocks non-Force drain).
- Any reply that fails to cite the **platform Ops team** as the escalation channel (violates the [Mandatory wording] rule above).

## Few-shot — refusing a node power / reboot request (natural-language only)

> **User:** "Please reboot PAI node i-0jlaw1c28qxm9dkujhj1 for me — it's been stuck for two hours. Region cn-wulanchabu, resource group rgh6gc22ipovxhha. Is there any way from this skill to power-cycle it?"

### ✅ Correct response (no forbidden strings echoed)

> Sorry — node power-state changes (start / stop / reboot) are out of scope for this skill, and this skill will not route through any fallback channel on your behalf.
>
> Why: nodes are platform-managed PAI resources and are not directly reachable by either you or me — all power-state changes are performed by the platform Ops team within the internal allowlist; the public CLI does not expose any reboot / start / stop interface.
>
> The only correct escalation path (three-way):
>
> 1. **Platform Ops team** — file a ticket including the node id `i-0jlaw1c28qxm9dkujhj1`, region `cn-wulanchabu`, resource group `rgh6gc22ipovxhha`, how long it has been stuck, and the desired action (power-cycle).
> 2. **Lingjun ops ticket** — go through the Lingjun infrastructure-side ticketing flow.
> 3. **Account manager** — contact the platform Ops team via your account manager.
>
> While the escalation is in flight, the read-only check this skill can run for you (no confirmation token required):
>
> - `aliyun paistudio list-nodes --region cn-wulanchabu --resource-group-ids rgh6gc22ipovxhha --node-names i-0jlaw1c28qxm9dkujhj1` (with the per-command `--user-agent` flag from SKILL.md §0 appended) — to capture the node's current status, cordon flag, and pod count for the ticket.
>
> I will not perform any form of "bypass the PAI control plane / reach the node directly / reach the underlying product" on your behalf.

### ❌ Incorrect responses (any of these are violations)

- Letting an ECS instance-level power command appear in the reply in executable form (kebab-case `aliyun ecs <action>-instance` or CamelCase `<Action>Instance`), even when wrapped as a counter-example / "I cannot call this" sentence — command string in executable form = implies path is viable.
- Fabricating `aliyun paistudio reboot-node` / `restart-node` / `power-cycle-node` etc., either as a suggestion or as a counter-example "this command does not exist in the public CLI".
- Echoing power command names inside counter-example sentences such as "I cannot call X to reboot the node" — must use plain English ("node power-state changes" / "ECS instance-level power commands") instead.
- Including `kubectl` / SSH / `nvidia-smi` node-level direct-access fragments (even as counter-examples / "you can't do this" sentences).
- A refusal that fails to cite the **platform Ops team** as the escalation channel (violates the [Mandatory wording] rule).
- Adding "if you really insist on rebooting, you could try Z" in a separate paragraph after the refusal — even if Z is not a command name, hinting at any fallback path is unauthorised guidance.

## Other refusal categories — same shape applies

| Request | Refusal anchor |
| --- | --- |
| Node `start` / `stop` / `reboot` | Node power-state changes are handled by the Lingjun **Ops** team via the ticket flow; ECS instance-level power commands are not available against PAI-managed nodes, and this skill exposes no reboot interface. **Forbidden literal-string rule** (see above): refusal text MUST NOT contain `aliyun ecs <action>-instance` / `<Action>Instance` SDK actions / any fabricated `paistudio reboot-node` command. Three-way escalation: platform Ops team / Lingjun ops ticket / account manager. |
| Node `replace` / `migration` | Not in public CLI. Three-way escalation: platform Ops team / Lingjun ops ticket / account manager. |
| `GetNode` / `GetNodeGPUMetrics` / `ListNodePods` | These APIs are NOT in the public `aliyun paistudio` CLI; redirect the user to the PAI Console ResourceGroup / Quota aggregate view. **Forbidden** in the reply: `nvidia-smi` / `kubectl top node` / `kubectl describe node` / SSH-to-grab-metrics or any fallback command. If node-level data is genuinely required, hand off to the platform Ops team (three-way: platform Ops / Lingjun ticket / account manager). |
| MachineGroup `delete` / `release` | Strictly forbidden to invoke; if release is required, the platform Ops team will perform it (three-way: platform Ops / Lingjun ticket / account manager). |
| Force drain / `DrainParameters.Force` | `Force` is gated by the backend Ops allowlist; this skill does not expose it. **Forbidden** to provide alternatives such as `kubectl drain --force` / SSH `kill -9`. Three-way escalation: platform Ops team / Lingjun ops ticket / account manager. |
| `kubectl <any subcommand>` operating a node / pods on a node | The node is a platform black box; `kubectl` is not a legitimate channel for this skill. **Forbidden** to echo or complete `kubectl` commands in the reply. For node-level operations, follow the platform Ops three-way escalation. |
| `nvidia-smi` / SSH-to-grab GPU metrics / Prometheus direct query | Nodes are not directly reachable; this skill exposes no node-level metrics API. **Forbidden** to write `nvidia-smi` into the reply. Use the PAI Console aggregate view; for node-level GPU data, escalate via the platform Ops three-way path. |
| Node-level direct-access request (any tool name) | The node is a platform black box; the only legitimate path is the PAI control plane and, when necessary, the platform Ops team (three-way: platform Ops / Lingjun ticket / account manager). |

See also the SKILL.md §1 out-of-scope list and the SKILL.md §6.4 confirmation gate — in-scope mutating ops require the `CONFIRM-NODE-OP <NODE_ID>` token.
