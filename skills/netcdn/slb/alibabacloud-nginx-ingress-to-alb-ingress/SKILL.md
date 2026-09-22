---
name: alibabacloud-nginx-ingress-to-alb-ingress
description: |
  Alibaba Cloud ALB Ingress Migration Skill. Migrate Kubernetes nginx Ingress resources to Alibaba Cloud Application Load Balancer (ALB Ingress, requires AlbConfig + IngressClass + Ingress).
  Users provide Ingress YAML (paste, file, or directory) — no cluster access required.
  Covers annotation compatibility classification, ALB-native annotation mapping, instance/listener-side configuration, path and order semantics, AlbConfig + IngressClass + Ingress generation, and a migration report with DNS weighted cutover.
  Triggers: "nginx ingress migration", "ALB compatibility", "ALB support check", "ingress-nginx to ALB", "switch to Application Load Balancer", "AlbConfig generation", "nginx迁移ALB", "nginx 迁移 ALB", "ALB Ingress迁移", "ALB Ingress 迁移", "切换到 ALB", "替换为 ALB", "AlbConfig生成", "AlbConfig 生成", "ALB 配置清单", "Ingress兼容性分析", "Ingress 兼容性分析", "入口规则适配", "注解适配审查", "annotation兼容性", "annotation 兼容性", "迁移评估", "切换可行性", "Nginx Ingress 迁移", "迁移到 alb ingress", "转成 alb ingress", "转成 ALB Ingress", "迁移到 ALB", "ingress 迁移".
---

# Nginx Ingress to ALB Ingress Migration

## Scenario Description

Migrate Kubernetes nginx Ingress resources to Alibaba Cloud ALB Ingress. ALB Ingress is a fully-managed L7 load balancer driven by three resources: a cluster-scoped **AlbConfig** (the ALB instance + listeners), an **IngressClass** bound to it, and the **Ingress** objects themselves.

This skill classifies every `nginx.ingress.kubernetes.io/*` annotation into **auto-converted / behaviour-changed / unsupported**, resolves unsupported annotations through a four-level decision tree (ALB-native annotation → safe to drop → ALB instance/listener-side configuration → manual work required), generates the migrated AlbConfig + IngressClass + Ingress YAML, and produces a deployment-ready migration report including the DNS weighted-cutover plan.

**Architecture**: `nginx Ingress Controller (CLB)  →  ALB Ingress Controller  →  AlbConfig + IngressClass + Ingress  →  ALB instance`

The core analysis workflow operates entirely offline on user-provided YAML — no cluster access, CLI tools, or cloud credentials required.

> **Why migrate**: ACK no longer maintains the Nginx Ingress Controller component. ALB Ingress is fully managed: no operations burden and better elasticity.

## Installation

This skill operates entirely offline on user-provided YAML. No CLI tools, SDKs, or cloud credentials are required.

On-demand tools (only when the workflow reaches a step that needs them):

| Tool | When needed | Check command | Minimum version |
|------|------------|---------------|-----------------|
| python3 | Only for `scripts/analyze-ingress-offline.sh` | `python3 --version` | >= 3.8 |
| PyYAML | Same, and **optional** — parsing is more accurate with it; without it the script falls back to line scanning | `python3 -c "import yaml; print(yaml.__version__)"` | >= 5.0 |

> **Do NOT pre-check or prompt installation of any tool.** If python3 is missing, say the helper script
> was skipped and read the YAML directly — never stop to ask the user to install something.

**Which path to take depends on how the input arrived:**

| Input | What to do |
|---|---|
| **Pasted** YAML in the conversation | Parse it directly. **Do not** write it to a temp file to run the helper script on — there is nothing the script adds that reading the paste does not already give you, and running it over your own copy is **not** independent corroboration of your classification: it reads the same bytes by the same rules, so quoting it back as an authority only makes a wrong answer look sourced |
| A **file path** | Run `scripts/analyze-ingress-offline.sh <path>` first for a per-annotation first pass, then read the YAML for the batch-level conclusions the script does not produce |
| A **directory path** | Same, with the directory as the argument — this is where the script earns its keep, since it walks every `.yaml`/`.yml` for you |
| **Nothing** — no paste, no path | Ask for it. See the input-failure table at the end of this step |

> 🚨 **The input is only ever what the user pointed at. Never go looking for one.** This skill package ships YAML of its own — `evals/fixtures/single-ingress.yaml`, `evals/fixtures/manifests/*.yaml`, `related_apis.yaml`, plus the examples inside `references/` — and those files are visible from the working directory. They are eval fixtures and documentation, **not anybody's cluster**.
>
> So when the user gave no input, do **not** scan the working directory, the skill directory, `$HOME` or anywhere else for "an Ingress that looks like it might be the one", and do not fall back to a fixture because it parses cleanly. Converting a fixture produces a complete, confident, entirely fabricated migration plan for an Ingress the user does not have — the worst failure this skill can commit, because nothing in the output looks wrong. Ask instead.
>
> Scanning a directory is correct only when **the user named that directory**.

## Environment Variables

No environment variables required. This skill does not invoke any cloud APIs or CLI tools.

## Authentication

Not applicable. This skill does not invoke Alibaba Cloud APIs or CLI. No credentials are needed.

## RAM Policy

Not applicable. This skill operates entirely on local YAML files and does not call any cloud APIs. See `references/ram-policies.md`.

## Parameter Confirmation

> **This skill only performs analysis and code generation — it does NOT execute any deployment or cluster write operations.**
>
> When the user provides Ingress YAML, proceed immediately with the full workflow (Step 1→5) and output the complete result. Do NOT ask for RegionId, vSwitch ID, or any other parameter. Use `<REGION>`, `<VSW_ID_ZONE_A>` / `<VSW_ID_ZONE_B>` placeholders in the output.
>
> **Never ask permission to produce output — just produce it.** Not "shall I analyse this Ingress", not "shall I generate the migrated YAML", not "do you want AlbConfig / IngressClass too" (all three are mandatory), not "shall I add the checklist and cutover plan", not "please confirm RegionId / vSwitch ID" (use placeholders).
>
> The one and only time to ask the user something is **Step 1 with unreadable input** (see that step's input-failure table). There you must ask a question, not hand over a self-service how-to.

| Parameter Name | Required/Optional | Description | Default Value |
|---------------|------------------|-------------|---------------|
| Ingress YAML | Required | nginx Ingress YAML to migrate (paste, file, or directory) | — |
| IngressClass name | Optional | Target IngressClass / AlbConfig name | `from--nginx` |

> **When Ingress YAML is not provided**: if the user asks about migration but provides no YAML, reply with the
> ask-for-input sentence given verbatim in Step 1. Do NOT abort the conversation — guide the user to provide the input.

## Core Workflow

> **Output conventions — they bind every reply, including one that stops early.**
>
> 1. **Report language — the generated report must be Chinese.** These instructions are written in English; what they ask you to *emit* for the user is Chinese prose. Keep code blocks, annotation names, ALB field names, paths and verbatim stderr as they are.
>    The user-facing output **is the body of this reply**, not a file you wrote. A Chinese report in `outputs/*.md` plus an English reply does **not** satisfy this — the reply is what gets read; a file is only a copy and its language cannot stand in. The scope is **every human-readable word in the message**: the opening note, the closing file list, outstanding-confirmation sections, transitions. Never "Chinese report with an English open and close". Failure messages included.
> 2. **Copy the four markers literally** — 🟢 / 🟡 / 🔴 / 🚫. Never substitute ✅ / ❌ / ⚠️ or words like "supported / unsupported" (Step 2).
> 3. **The deliverable goes in the reply.** The compatibility table, all three resources' YAML and the summary must appear in the response body; writing a copy to disk is optional, and the reply may not degrade into "written to xxx.md". **The three resources may be neither omitted nor truncated**: each carries its own `kind:` line, every generated Ingress appears (including the `defaultBackend` catch-all), and nothing stands in for a block — no "rest omitted", no "same as above", no "…" (Step 5).
> 4. **Say it all in one go** — no asking for approval before producing.
>    This holds for a **correction round** too. After the user confirms or corrects something, **re-send all three resources in full**; do not reply with a list of which lines in which files changed. That is the same degradation as "written to xxx.md" wearing another shape. The user must finish every round holding one appliable copy instead of mentally merging last round's YAML with this round's diff. Re-send even when only comments moved, and say the semantics did not change.
> 5. **Never present an inference as a measurement.** Only conclusions this document or `references/` explicitly marks as measured may be called measured or verified in the report. Everything else is "the rule says" or "must be verified". In particular do not dress up an offline `re.fullmatch`, a paper argument, or "the rule implies it" as a cloud-side test: this environment usually has **neither a cluster nor internet access**, so any claim of having hit a real ALB is false. A wrong attribution is worse than a wrong conclusion, because the user skips verification on the strength of it.
>
> **Given YAML, run Step 1→5 to completion in a single response.** No confirmation between steps, no pausing to ask. The migration report, cutover plan and checklist are standard output, not optional extras. Unspecified parameters become `<REGION>` / `<VSW_ID_ZONE_A>` placeholders. The only required input is the Ingress YAML itself.

### Step 1: Parse Ingress YAML

Accept YAML from any of the following input formats:
- Direct paste in conversation (with or without markdown code fences)
- File path (e.g., `ingress.yaml`, `./k8s/ingress.yaml`)
- Directory path (scan all `.yaml`/`.yml` files for Ingress resources)
- Multi-document YAML (separated by `---`)
- Partial YAML (missing `apiVersion`/`kind` — infer as Ingress if `annotations` with `nginx.ingress.kubernetes.io/*` are present)

**When the input cannot be read, stop and hand it back — never invent YAML.**

Reading the input is the one step with no safe fallback: with no source Ingress there is nothing to convert, so a migration report produced anyway would be fabricated. Note this is the *opposite* of the rule in Step 2 — content that can be read but cannot be expressed on ALB is still converted as far as it safely goes. The distinction is "no input" versus "awkward input".

| What happened | What to do |
|---|---|
| The file or directory does not exist, or permission is denied | Report the exact path and the error, then ask the user to check it or paste the YAML instead |
| The path contains spaces or shell metacharacters and the helper script rejected the argument | Report the argument error, ask for a quoted or corrected path, or offer to take pasted YAML |
| The helper script exits non-zero or crashes | Report its stderr verbatim. If the file itself is readable, the script is only an aid — carry on by reading the YAML directly and say the script was skipped. If the file is *not* readable, hand back to the user |
| A directory holds no `.yaml`/`.yml` file, or none of them contains an Ingress | Say so, naming the path and how many files were scanned; do not guess at a different location |
| The file parses but holds no Ingress (only Service / Deployment / …) | List the kinds that were found and ask for the right file |
| The YAML is syntactically invalid | Report the parser error with line and column, and ask for a corrected file |

In every one of these rows, **do NOT output AlbConfig / IngressClass / Ingress YAML**, and do not present a placeholder-only skeleton as if it were a result. Retrying once after the user corrects the input is fine.

> A failure message is user-facing output too, so two of the Core Workflow conventions bind here — and you will not reach Step 5 if you stop, hence the reminder. **The message you emit must be Chinese prose** (paths, verbatim stderr and commands stay as they are), and **end with an actual question** — ask the user to confirm the path or paste the Ingress YAML straight into the chat. A paragraph of "here is how to re-run it" is not a question: what the user needs at this point is to be asked, not handed a self-service guide.

For each Ingress found, extract:
- all `nginx.ingress.kubernetes.io/*` annotations (plus legacy `kubernetes.io/ingress.class`)
- `spec.rules[].host`, `spec.rules[].http.paths[]` (including `path` and **`pathType`** — pathType decides the path conversion semantics, see Step 4)
- `spec.tls`, `spec.ingressClassName`, `namespace`
- **`spec.defaultBackend`** — it produces an extra catch-all Ingress (`from--<name>--default`), **scoped to the named hosts the source declares** rather than one empty-host rule matching every domain. ⚠️ **Never just leave `spec.defaultBackend` on the generated Ingress and call it carried over** — the ALB controller reads that field in only two places, a Service-to-Ingress reverse index used for watch triggering and `isCatchAllIngress`, which merely gates the `--disable-catch-all` flag; **no code path turns it into a forwarding rule** (verified in the controller source). So the field is accepted, reconciles clean, and routes nothing: unmatched paths answer 404 instead of reaching the default Service, with no event or error to show why. Generating the extra Ingress is the only way the backup survives. Three shapes:

  | Source shape | Catch-all produced |
  |---|---|
  | Rules with named hosts | One `<host>` + path `/` (Prefix) per named host |
  | **No rules at all** (pure defaultBackend) | One **empty-host** rule + path `/` — this is nginx's global `_` default server |
  | Rules exist but **all host-less** | **Nothing** — nginx discards the defaultBackend in that shape too |

  > Another live-verified detail: **for a declared named host whose Ingress has no `defaultBackend`, an unmatched path falls to nginx's own global default backend (404), not to the `_` server**. So "a pure-defaultBackend Ingress serves `_`" only affects **undeclared** domains; it never backs up an already-declared host. Do not conflate the two kinds of fallback during migration.

  > Basis (verified on a cluster): nginx's `spec.defaultBackend` only backs up unmatched paths **on the named hosts that Ingress itself declares**; **an unknown domain never hits it** (it falls to the cluster's global default backend). An empty host on ALB carries no host condition and therefore **matches every domain**, so copying it verbatim would send unknown-domain traffic to the defaultBackend as well — wider than nginx. Also verified: a host-less rule is served by nginx's `_` default server, but the defaultBackend is **never attached to `_`**, which is why it is discarded when every rule is host-less.

**If the user's message mentions migration/analysis but does NOT include any YAML**, do NOT abort or error out. Reply with the full picture and include the sentence below verbatim — opening or closing line, whichever reads better. The reply still owes the user everything the input-failure table requires: what you checked, that nothing was generated, and that you did not substitute a shipped fixture. The sentence is the ask, not the whole answer, and the reply must end on a question either way.

```text
请提供需要迁移的 nginx Ingress YAML（可以直接粘贴、提供文件路径或目录路径）。
```

> **The helper script** (`scripts/analyze-ingress-offline.sh <file|dir>`, used for file and directory
> input per the table above) prints the 🟢/🟡/🔴 classification and 🚫 downgrades per Ingress, with zero
> dependencies (more accurate with PyYAML, falls back to line scanning without it). Treat its output as a
> first pass, not the verdict: it judges by **value**, not just by key — boolean
> values, the `limit-rps` and `cors-max-age` ranges, grpc missing `spec.tls`, `canary-weight` scaled by
> its total, `load-balance` overridden by uch, and the `ssl-redirect` added when a `tls:` block exists.
> It is still a **single-Ingress view** — cross-Ingress regex tainting of a host (and the 🟡 it puts on
> the tainted neighbour), order, and splitting are batch-level conclusions it does not produce; use the
> Step 4 rules for those. Without PyYAML it cannot parse `spec.tls`, and in that case it says so
> explicitly rather than guessing.

### Step 2: Classify Annotations

Classify every annotation into 🟢 / 🟡 / 🔴. See `references/annotation-mapping.md` for the complete lookup table. (Usually one verdict per annotation, but a few produce two — see the `rewrite-target` note at the end of this section.)

> **These four characters are the report's vocabulary — copy them literally, never substitute.** 🟢 converted, 🟡 behaviour change, 🔴 unsupported, 🚫 downgraded. Do **not** swap in ✅ / ❌ / ⚠️ / ⛔, words meaning "supported" / "unsupported" in any language, or a colour named in text: the migration report is read and diffed against the offline script's output, which emits exactly these four, and a substituted glyph makes an otherwise correct classification unrecognisable. (Note the ✅/❌ used inside `references/acceptance-criteria.md` mark *its own* right-and-wrong examples — they are not report markers.)

> **Important: 🔴 is about *why* an annotation leaves the output, not the mere fact that it left.** Exactly two grounds make it 🔴: it configures a different ingress controller (`nginx.ingress.kubernetes.io/`, `nginx.org/`, `nginx.com/`, `ingress.kubernetes.io/`), or it would make an external controller fight the still-present source Ingress over one resource (`cert-manager.io/`, `external-dns.alpha.kubernetes.io/`). So a newly added upstream nginx annotation is always reported and never silently lost; during analysis, do **not** assume an annotation is safe just because it is absent from a list.
>
> Every other annotation that no feature consumed (in-house keys such as `mycompany.com/owner`, `prometheus.io/scrape`) is **copied through verbatim and reported 🟢 carried over**, not 🔴 — it is still on the object, so calling it unsupported is untrue, and since any single 🔴 pushes the whole batch to `PartialSuccess`, one unrelated annotation would stop a clean migration from ever reporting `Succeeded`. Packaging / GitOps metadata (`kubectl.kubernetes.io/`, `app.kubernetes.io/`, `helm.sh/`, `meta.helm.sh/`, `argocd.argoproj.io/`, `fluxcd.io/`, `kustomize.toolkit.fluxcd.io/`) is neither reported nor removed. **A 🟢 annotation whose target comes out empty is still 🟢, never 🔴.** `ssl-redirect: "true"` on an Ingress with no `spec.tls` is the standard case: nginx was not redirecting either, so the correct output carries no `alb.../ssl-redirect` — the feature is a faithful no-op, not an unsupported one. Put 🟢 in the compatibility table and say the target is empty; marking it 🔴 tells the user a capability was lost when nothing was.

| Category | Count | Action | Example |
|----------|-------|--------|---------|
| 🟢 **Auto-converted** | 20 | Rewritten to the matching ALB annotation and kept | `rewrite-target`, `enable-cors`, `canary-weight`, `ssl-redirect` |
| 🟡 **Behaviour change** | **6 trigger conditions** (see `annotation-mapping.md` §2) | Converted, but the semantics may differ — needs human confirmation | `limit-rps` (always), `use-regex`/`rewrite-target` once regex applies, `GRPCS`, `cors-max-age` clamped, `canary-weight` together with `canary-by-header`/`-by-cookie`, `load-balance` overridden by `uch` |
| 🔴 **Unsupported** | **whatever gets removed** (the two grounds above) | Not converted → follow the Step 3 decision tree | `server-snippet`, `auth-url`, `affinity`, `proxy-body-size`, `enable-modsecurity` |

> **One annotation can carry two verdicts.** `rewrite-target` does exactly this once regex applies: one 🟢 (`rewrite-target` → `alb.../rewrite-target`, the path rewrite itself converts) plus one 🟡 (`rewrite-target` → `alb.../use-regex`, because it switched that host into regex matching and ALB's regex is case-sensitive). Report both; do not report only the 🟢.

> **Besides the three categories there is a fourth marker, 🚫 — a downgrade, not a refusal.** These are
> not annotation problems: the path or the backend itself cannot be carried over faithfully. **Always
> still produce all three resources.** Apply the repair in the table, and list every repair in a
> dedicated report section so a human confirms it before applying. Handing back nothing is not an
> option — the user came for migrated YAML.
>
> | Situation | Repair to apply | What to flag as 🚫 |
> |---|---|---|
> | Path contains regex metacharacters and no Ingress on that host sets `use-regex`/`rewrite-target`. **With the ingress-nginx validating webhook running, this shape is always `pathType: ImplementationSpecific`** — the webhook rejects regex characters on `Prefix` outright (`path /dl/(.*) cannot be used with pathType Prefix`, verified live) | Emit the path **unchanged** on `pathType: Prefix` and add `alb.ingress.kubernetes.io/use-regex: "true"` | The path is now a regex on ALB. ALB's regex is **case-sensitive** while nginx's `~*` is not, so verify any path with mixed case. **Never emit such a path as a literal**: ALB answers `code: 400, The param of Rules.N...PathConfig.Values.K is illegal` and that error stops rule updates for the **entire load balancer** — verified live, a valid Ingress created during the freeze still 503'd after 190s and recovered 50s after the illegal one was deleted |
> | Path contains `*` or `?` and the host is not in regex mode | Emit the path unchanged | nginx matches these two characters literally, ALB matches them as **wildcards**, so the same path answers a different set of requests. Offer the regex form (`use-regex` + an escaped pattern) as the faithful alternative |
> | A path has **no `pathType`** | Emit `pathType: ImplementationSpecific` — the closest match to what nginx does with an unset type | The match mode was **guessed**. `Prefix` and `Exact` would each give a different hit set; have the user confirm |
> | A rule has a host but no `http` section, and the Ingress has no `defaultBackend` | Emit every other rule; drop this one | That host routes nothing. Ask whether it was meant to have paths or a defaultBackend |
> | `defaultBackend` is not a Service backend (`defaultBackend: {resource: {...}}`) | Emit the rules; skip the catch-all Ingress | ALB forwarding rules cannot express a resource backend, so the unmatched-path fallback is gone. Suggest a Service that fronts the resource |
> | `backend-protocol: GRPC`/`GRPCS` but the Ingress has **no `spec.tls`** | **Strip `backend-protocol`** and emit a plain HTTP Ingress | gRPC is lost. The controller's `checkIngressProtocolAnnotations` demands `ssl-redirect: "true"` for grpc on an HTTP listener, and the error from `buildServerGroupSpec` **fails the whole AlbConfig model build**, stopping rules for every Ingress on that ALB. Tell the user to add `spec.tls`, then re-add `backend-protocol: grpc` |
> | **A boolean annotation whose value is not a boolean** (`ssl-redirect: "on"`, `enable-cors: "yes"`) | Strip that one annotation | Name the annotation and its original value. ALB's webhook would reject the whole Ingress for it (`the value on is invalid. Please set the value as one of: [true false]`); nginx cannot parse it either. Ask the user to write `true`/`false` and re-run |
> | **Four-layer needs**: `ssl-passthrough`, a `server-snippet` carrying a `stream {}` block, or a reference to `tcp-services`/`udp-services` | Strip it and emit the HTTP routes | 🚫 Report it with the required phrase for a failed conversion listed in the Step 5 block, not a paraphrase of your own — ALB listeners are only `HTTP`/`HTTPS`/`QUIC`, so TCP/UDP proxying cannot move to ALB Ingress at all. Then, under the required alternative-suggestion label from that same block, carry that traffic on an **NLB or CLB layer-4 listener**, which no longer goes through the three resources and needs its entry point and DNS planned separately.(A `stream {}` block nested inside an http `server-snippet` does not work on nginx either, so the HTTP routes of such an Ingress are usually the only part that was ever live) |
> | Two sources would **produce the same object name** — in one namespace, `a` (with `defaultBackend`, producing `from--a--default`) plus an Ingress literally named `a--default` | Append a numeric suffix to disambiguate (`from--a--default-2`) | Both objects are named by the tool, not the user. Say which two sources collided so the user can rename one and re-run for a stable name. Collisions come from the suffixes `--default`, `--regex`, `--nohost`, `--p<N>` |
>
> **The one hard rule**: never emit a path ALB validates as a literal when it holds regex metacharacters. Every other row degrades; that one would freeze the customer's load balancer.

> **Why an illegal boolean value is a 🚫 downgrade rather than a plain 🔴.** Four annotations are read by
> ALB as the literal strings `"true"`/`"false"`: `canary`, `enable-cors`, `cors-allow-credentials`,
> `ssl-redirect`. Only spellings `strconv.ParseBool` accepts are allowed (`true`/`True`/`TRUE`/`1`/`t`/`T`
> and the false equivalents); **`on`/`yes`/`maybe` and friends all fail.**
>
> Stripping it is the only safe repair, because **there is no faithful value to translate to**:
> - nginx cannot parse it either and **falls back to the global default in its ConfigMap**, so what the
>   source Ingress does today depends on a ConfigMap this skill cannot read (verified on a cluster: with a
>   certificate, `true`/`1` redirect 308 while `on`/`yes` answer 200);
> - dropping it silently bets that the global default is off; translating it to `true` bets the user meant on;
> - copying it verbatim produces an object ALB's admission webhook **rejects entirely**
>   (`the value on is invalid. Please set the value as one of: [true false]`).
>
> So strip it, emit the rest of the Ingress, and report the annotation with its original value under 🚫 so
> the user writes `true`/`false` and re-runs. **This affects one annotation on one source; everything else
> converts normally.**

> **Annotation and label inheritance: everything is copied except the prefixes below.** The output is a new object; the source Ingress is untouched.
>
> | Prefix not copied | Reason |
> |---|---|
> | `nginx.ingress.kubernetes.io/`, `nginx.org/`, `nginx.com/`, `ingress.kubernetes.io/` | They configure a different ingress controller; ALB never reads them, and leaving them looks like they still apply |
> | `kubernetes.io/ingress.class` | The class name now lives in `spec.ingressClassName` |
> | `cert-manager.io/`, `external-dns.alpha.kubernetes.io/` | The source Ingress is still present during migration, so two Ingresses would fight over the same certificate Secret / DNS record |
>
> Labels are all copied except the single key `ingress-controller` (whatever its value): the most natural clean-up at the end of a migration is `kubectl delete ing -l ingress-controller=nginx`, which would take the generated objects with it if they inherited that label. Full rules, with the live-verified basis, in `references/generated-resources.md` §4.1.
>
> ⚠️ **Decide who renews the certificate before deleting the source Ingress**: the generated Ingress still references the same `spec.tls.secretName`, so HTTPS keeps working during the migration (renewed by the cert-manager annotations on the source). Once the source is deleted, no Ingress is responsible for that Secret any more and HTTPS breaks when the certificate expires — and not before.

**Per-annotation lookup lives in `references/annotation-mapping.md`** — all 20 auto-converted entries with their 🟡 conditions, every 🔴 with its decision-tree destination, and the source citations. Open it for any annotation not resolved by the category table above; do not guess from the category alone.

**Baseline counts** — upstream ingress-nginx documents **130** annotations and `annotation-mapping.md` is generated against that list: **20** auto-converted (complete table below), **6 trigger conditions** for 🟡 (§2 of that file, not 6 annotations), and the rest 🔴 — of which 9 have an ALB-native annotation, 3 are safe to drop, 8 move to the instance/listener side, and the remainder need manual work (Step 3).

> ⚠️ 🔴 is a **catch-all verdict, not a closed list**: any annotation that no feature consumed is reported, whatever its prefix. A newly added upstream annotation, or an in-house `<domain>/*` key, lands here too.

**Complete list — all 20 auto-converted annotations (prefix `nginx.ingress.kubernetes.io/` → `alb.ingress.kubernetes.io/`):**

| nginx annotation | ALB annotation | Notes |
|-----------|---------|------|
| `canary` | `canary` | order is derived from its own path length and then moved two slots earlier — **not** a fixed value (see "order and batched migration" below) |
| `canary-by-header` | `canary-by-header` | |
| `canary-by-header-value` | `canary-by-header-value` | |
| `canary-by-cookie` | `canary-by-cookie` | |
| `canary-weight` | `canary-weight` | The value is scaled to a percentage using `canary-weight-total` (next row); a non-integer, or a total ≤ 0, means the annotation is dropped and reported 🔴. ⚠️ **Reported 🟡 when it appears together with `canary-by-cookie`/`canary-by-header`**: nginx allows the combination, ALB's semantics differ and there is no equivalent mapping, so the user must pick weight *or* header/cookie |
| `canary-weight-total` | **folded into `canary-weight`** | ALB reads `canary-weight` with **no denominator**, so the total has to be folded in here: `50/1000` is 5% to nginx and copying it verbatim means 50% to ALB (**10x the canary traffic**). A share that does not land on a whole percent is rounded and reported 🟡 |
| `enable-cors` | `enable-cors` | |
| `cors-allow-origin` | `cors-allow-origin` | |
| `cors-allow-methods` | `cors-allow-methods` | |
| `cors-allow-headers` | `cors-allow-headers` | |
| `cors-expose-headers` | `cors-expose-headers` | |
| `cors-allow-credentials` | `cors-allow-credentials` | |
| `cors-max-age` | `cors-max-age` | ⚠️ **ALB only accepts -1..172800, and nginx's own default of 1728000 is exactly 10x that maximum.** Above the maximum → clamped to `172800` and reported 🟡 (shorter preflight cache); non-integer or < -1 → dropped and reported 🔴. Copying an over-limit value makes ALB answer `The param of 1728000 is illegal` and **freezes rule updates for the entire load balancer** |
| `backend-protocol` | `backend-protocol` | ⚠️ **The value must be lower-cased**: nginx `HTTPS`/`GRPC` → ALB `https`/`grpc`. ALB matches case-sensitively, so an upper-case value silently downgrades to HTTP. `AUTO_HTTP`/`FCGI` have no counterpart (🔴); `GRPCS` needs confirmation (🟡). 🚨 **grpc has a further precondition**: the output must have a 443 listener and carry `ssl-redirect: "true"`, or the controller stops publishing rules for the whole ALB. When the source has `spec.tls` but no `ssl-redirect`, the tool **forces it on** and reports 🟡 — nginx was not redirecting, so this is a genuine behaviour change and the report must say so. When the source already wrote `ssl-redirect: "true"` it is reported 🟢. When the source has no `spec.tls`, or wrote `ssl-redirect: "false"`, **`backend-protocol` is stripped and a plain HTTP Ingress is emitted**, flagged 🚫 — see the downgrade table above |
| `load-balance` | **`backend-scheduler`** | Both key and value change: `round_robin`→`wrr` (also tolerated: `least_conn`→`wlc`, `ip_hash`→`sch`); **`ewma` has no ALB counterpart → 🔴, the algorithm must be chosen by hand**. ⚠️ **Reported 🟡 when `upstream-hash-by` was converted to `uch` and this annotation asked for something else**: ALB has a single scheduler field, so the consistent hash **overrides** it — to keep this algorithm, drop `upstream-hash-by` |
| `upstream-hash-by` | **`backend-scheduler-uch-value`** (and `backend-scheduler: uch` is set automatically) | ⚠️ ALB's consistent hash always hashes a **query-string parameter**, so only `$arg_<name>` converts (taking `<name>`); other variables such as `$request_uri` → 🔴 |
| `limit-rps` | **`traffic-limit-ip-qps`** | **Always reported 🟡**: both mean "per client IP per second", but the same number lets very different traffic through — nginx counts per replica and allows a 5x burst by default, ALB counts once and has no burst (measured with the same config: nginx let 39 through, ALB 3). A value outside ALB's 1–100000 is dropped and reported 🔴 |
| `ssl-redirect` | `ssl-redirect` | Applies when **the Ingress has a `spec.tls` block**, regardless of which hosts the certificate covers (verified on a cluster, see `annotation-mapping.md` §6.2). ⚠️ **Do not add this annotation when the source did not write it**: nginx's implicit default comes from the controller ConfigMap, and **ACK ships it as `ssl-redirect: false`** (verified: a host with a certificate and no annotation answers 200, not 308), so inventing it would turn working plaintext traffic into a 308. With no `tls:` block the annotation is dropped (nginx does not redirect either) |
| `use-regex` | `use-regex` | **Reported 🟡 whenever the output ends up matched by regex**: ALB's regex is **case-sensitive** while nginx's `~*` is not (verified: nginx serves `/images/x` from a `/Images` rule, ALB answers 503) |
| `rewrite-target` | `rewrite-target` | `$1` becomes `${1}`; `use-regex: "true"` is **added automatically**. ⚠️ **This annotation yields two rows, not one**: the path rewrite itself is 🟢, and because it switched the host into regex matching it is **also reported 🟡** keyed `rewrite-target` → `alb.../use-regex` (ALB's regex is case-sensitive, nginx's `~*` is not). Reporting only the 🟢 hides the case-sensitivity risk. The sole exception is a value equal to the path it sits on — nginx then rewrites nothing and does not enable regex, so there is no 🟡 |

Additional handling: `kubernetes.io/ingress.class` (the legacy class annotation) → the annotation itself is dropped and the class name is carried by `spec.ingressClassName`. In the report it is 🟢 **converted**, with the target written as `spec.ingressClassName` rather than some `alb.*` annotation — the only item whose destination is a spec field instead of an annotation.

> **If an annotation is NOT in the above table**, look it up in `references/annotation-mapping.md`. If still not found, classify as 🔴 unsupported and resolve via the decision tree in Step 3.

**Special value / semantic changes** (converted, but the semantics need confirmation):
- `rewrite-target`: nginx's `$1`/`$2` capture groups become ALB's `${1}`/`${2}`
- `backend-protocol`: **the value's case must be converted** — ALB matches this annotation case-sensitively and only accepts lower-case `https`/`grpc`; the upper-case spelling nginx users write falls through to the default branch and **the backend is silently downgraded to cleartext HTTP**
- `load-balance`: nginx's `ewma` has no ALB counterpart (ALB has only `wrr`/`wlc`/`sch`/`uch`), so the algorithm must be chosen by hand
- `upstream-hash-by`: ALB's consistent hash can **only** hash a query-string parameter and `uch-value` is the parameter name; therefore only `$arg_<name>` converts and `$request_uri` and friends cannot be expressed
- `canary-weight` together with `canary-by-header` / `canary-by-cookie`: nginx allows the combination, ALB's semantics differ — mark 🟡 behaviour change and require human confirmation
- `load-balance` together with `upstream-hash-by`: ALB has a single scheduler field (`backend-scheduler`), so the consistent hash (`uch`) **overrides** whatever `load-balance` asked for. The output is `backend-scheduler: uch` + `backend-scheduler-uch-value: <parameter>`, and `load-balance` is reported 🟡 because its value never took effect

### Step 3: Resolve Unsupported Annotations

For each unsupported annotation, follow this decision tree in order:

```
1. Is there an ALB-native annotation?      → rewrite with it (e.g. mirror-target → actions.traffic-mirror)
2. Safe to drop?                           → remove it (ALB's default behaviour already covers it)
3. ALB instance/listener/server-group?     → move it off the Ingress, onto AlbConfig or the server group
4. None of the above?                      → manual work (application change / ALB AScript / WAF)
```

See `references/migration-patterns.md` for the complete decision tree with per-annotation resolution.

**ALB-native replacements (each verified to exist in the controller source):**

| nginx annotation | ALB replacement | Notes |
|-----------|---------|------|
| `limit-rpm` | `alb.ingress.kubernetes.io/traffic-limit-ip-qps` | nginx rate-limits per **client IP**, hence ip-qps; divide the value by 60, and ALB's minimum is 1 QPS — anything under 60 rpm cannot be expressed. (`limit-rps` is an auto-converted item, see the Step 2 table) |
| `limit-connections` | `alb.ingress.kubernetes.io/traffic-limit-qps` | Total rate limit; concurrent connections ≠ QPS, so load-test to confirm |
| `mirror-target` | `alb.ingress.kubernetes.io/actions.<svc>` (`type: TrafficMirror`) | ⚠️ The target **can only be a server group** (`TargetType` has the single value `ForwardGroupMirror`), not an arbitrary URL; `mirror-request-body` and `mirror-host` have **no counterpart field and cannot be expressed** |
| `custom-headers` | `actions.<svc>` (`type: InsertHeader`) + **`rule-direction.<svc>: Response`** | ⚠️ Two preconditions: the value is a **ConfigMap reference** (`<ns>/<configmap>`, which has to be expanded into individual headers); and it acts on **client response headers**, so omitting the direction defaults to `Request` (upstream request headers) = no effect, while also pushing internal headers to the backend |
| `custom-http-errors` | **All three, none optional**: `rule-direction.<svc>: Response` + `conditions.<svc>` (`ResponseStatusCode`) + `actions.<svc>` (`type: FixedResponse`) | 🚨 **Omitting the direction takes that path down completely**: without it the direction defaults to `Request` and every request is replaced by the error page. And the webhook's "at least one final-type action" check **is only skipped in the `Response` direction**, so the wrong form publishes cleanly and is never caught |
| `permanent-redirect` / `temporal-redirect` / `force-ssl-redirect` / `app-root` | `alb.ingress.kubernetes.io/actions.<svc>` (`type: Redirect`) | The redirect code is specified inside the action |
| `default-backend` (**the annotation**) | `actions.<svc>` (`type: ForwardGroup` / `FixedResponse`), or an application-side fallback | ⚠️ Its semantics are "use this service when the rule's Service has **no active endpoints**", plus being the error-page source when `custom-http-errors` is also set. It is **not** `spec.defaultBackend` (the unmatched-path fallback, which the converter already handles). ALB has no "swap server groups when the backend is entirely down" switch, so it can only be approximated with health checks plus server-group orchestration |
| `whitelist-source-range` / `denylist-source-range` | `alb.ingress.kubernetes.io/conditions.<svc>` (SourceIp condition) together with `actions.<svc>` (`type: FixedResponse`) | ALB has 7 **usable** request-direction conditions: Host/Path/Header/QueryString/Method/Cookie/**SourceIp** (the response direction additionally has `ResponseStatusCode` and `ResponseHeader`). A `Model` type exists in the constant list but the annotation-facing struct carries no `ModelConfig`, so it cannot be built — never offer it as a target, see `migration-patterns.md`. ⚠️ Each of the three routes has its own constraint: ① a SourceIp `conditions` entry is the first choice, but **a canary Ingress may not carry any `conditions.*` annotation** — it reports `can't exist Canary and customize condition at the same time` and stops every rule on that listener from publishing; ② a listener ACL (`aclConfig`) is **listener-scoped**, so it becomes a global allow-list once several Ingresses share the ALB; ③ an instance security group (`securityGroupIds`) **cannot coexist** with an ACL (reconciliation reports `acl and securityGroupIds cannot use together` — not an admission rejection, so the object applies fine). See `migration-patterns.md` |
| `server-alias` | `alb.ingress.kubernetes.io/conditions.<svc>` (Host condition) or an extra rule | |

**Safe to drop:** `service-upstream`, `proxy-request-buffering`, and the buffering family `proxy-buffer*`

> ⚠️ **`proxy-next-upstream*` is NOT in "safe to drop" — check the value first.** ALB Ingress has **no retry configuration at all**, so dropping it does not mean "ALB has an equivalent"; it hands retries to the platform default with no way to tune them. It is only safe to drop when the value is exactly nginx's default (`error timeout` / `-tries: 0` / `-timeout: 0`); a value that widened the retry surface (including `http_5xx` and friends) loses those retries. **A value of `off` is the most dangerous** — a customer sets `off` precisely to prevent retries, and a non-idempotent endpoint (checkout, payment) could be submitted twice. This one needs a human. See `annotation-mapping.md` §4.7

**Move to the ALB instance / listener / server group:** `proxy-connect-timeout` / `proxy-send-timeout` / `proxy-read-timeout` (listener and server-group timeouts), `affinity` / `session-cookie-*` (server-group session persistence), `proxy-ssl-*` (server-group backend TLS), `enable-modsecurity` / `enable-owasp-core-rules` (AlbConfig `edition: StandardWithWaf` plus the WAF console), `enable-access-log` (AlbConfig `accessLogConfig`; the logStore name must start with `alb_`)

> ⚠️ This whole class shares a granularity mismatch: **the ALB side is mostly instance- or listener-scoped while the nginx annotation is per-Ingress.** WAF and access logs make it most obvious — turning them on covers every Ingress on that ALB, and there is no way to enable them for just one. Confirm that amplification is acceptable before several source Ingresses share one AlbConfig.

> ⚠️ **`ssl-passthrough` does not belong to this class** — ALB's listener protocols are only `HTTP` / `HTTPS` / `QUIC`, with no TCP/SSL, so changing the protocol on ALB is impossible. That traffic has to **move to CLB or NLB (layer 4)**, at which point it no longer goes through the three resources and its entry point and DNS need separate planning.

**Manual work required (no counterpart at the ALB Ingress annotation layer):** `auth-*` (**25 annotations**, authentication and authorization), `configuration-snippet` / `server-snippet` / `stream-snippet` (raw nginx directives), `upstream-vhost`, `limit-rate`, `canary-by-header-pattern`, `mirror-request-body` / `mirror-host` (ALB's mirror configuration has no matching field)
> Directions: reimplement in the application, use ALB **AScript** programmable scripting, or put WAF in front. **Check the official documentation for the specific capability; never assert an unverified annotation name to the user.**

### Step 4: Generate Migrated Resources

ALB Ingress needs **all three resources**; none is optional. See `references/generated-resources.md` for the full spec and placeholder list.

The reference chain is `Ingress.spec.ingressClassName` → `IngressClass.metadata.name` → `IngressClass.spec.parameters.name` → `AlbConfig.metadata.name`, all four carrying the same name (`from--nginx` by default, or `from--<ingress-name>` when the source declared no class). `IngressClass.spec.controller` is the fixed value `ingress.k8s.alibabacloud/alb`.

**The complete annotated example of all three objects — including `zoneMappings`, the `converted/ingress2albconfig` tag, `listen-ports` and `order` — is in `references/generated-resources.md`.** Work from that example rather than reconstructing it from memory, and keep `listen-ports` in exact agreement with the AlbConfig `listeners`.

```yaml
# 1. AlbConfig — cluster-scoped: the ALB instance and its listeners
apiVersion: alibabacloud.com/v1
kind: AlbConfig
metadata: {name: from--nginx}
spec:
  config:
    name: from--nginx
    edition: Standard                # Basic / Standard / StandardWithWaf only
    addressType: <ADDRESS_TYPE_Internet_or_Intranet>   # never ship a value here: an omitted or guessed one silently means public
    accessLogConfig: {}
    tags: [{key: converted/ingress2albconfig, value: "true"}]
    zoneMappings:                    # real vSwitch IDs, same VPC, two different zones
      - {vSwitchId: <VSW_ID_ZONE_A>}
      - {vSwitchId: <VSW_ID_ZONE_B>}
  listeners:
    - {port: 80, protocol: HTTP}     # add {port: 443, protocol: HTTPS} when the source has spec.tls
---
# 2. IngressClass — cluster-scoped: bound to the AlbConfig above
apiVersion: networking.k8s.io/v1
kind: IngressClass
metadata: {name: from--nginx}
spec:
  controller: ingress.k8s.alibabacloud/alb   # fixed value, do not change
  parameters: {apiGroup: alibabacloud.com, kind: AlbConfig, name: from--nginx}
---
# 3. Ingress — one per source Ingress, plus any --default / --p<N> split
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: from--<source-name>
  namespace: <source-namespace>
  annotations:
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80}]'   # must match the listeners exactly
    alb.ingress.kubernetes.io/order: "795"                    # 800 - min(pathLen,158)*5
spec:
  ingressClassName: from--nginx
  rules: ...                         # hosts and paths from the source, converted per the table below
  tls: ...                           # kept from the source; the controller uploads the Secret itself
```

**Where the filled-in objects go: into the body of your reply**, as three complete YAML blocks under Step 5 item 2 — not into a file with a summary standing in for them. Writing a copy to `outputs/` as well is fine; replacing them with a file list is not. Convention 3 governs this, and it is the single most common way this skill's output has failed.

> **`order` is not optional.** ALB matches in ascending order and returns on the first hit; it does not prefer the longer path the way nginx does. Without the annotation the controller gives every Ingress the default of 10 and breaks ties by name, which swaps "the more specific rule wins" for alphabetical order. The formula, and the handling of canary and splits, are in `references/generated-resources.md` §5b.
>
> **Decide whether the host is in regex mode before rewriting paths and pathType** — the same source path produces completely different output in the two modes. Outside regex mode, a path containing `( ) [ ] { } | ^ $ \` or `* ?` may **never be emitted as a literal** (full list in `generated-resources.md` §5.3; `.` and `+` are not on it) — but it is **not** a reason to refuse the Ingress: apply the matching 🚫 repair from Step 2 and emit all three resources. Full rules in `references/generated-resources.md` §5.1–5.3.

**Path conversion rules — the easiest thing to get wrong. Decide whether the host is in regex mode first, then decide how to write the path:**

| Host in regex mode? | Source pathType | Output path | Output pathType |
|---|---|---|---|
| **Yes** (any Ingress on that host carries `use-regex`/`rewrite-target`) | any, including `Exact` | **unchanged** | **`Prefix`** + stamp `use-regex: "true"` |
| No | `Prefix` / `Exact`, path free of the §5.3 characters | unchanged | unchanged |
| No | `ImplementationSpecific`, path **non-empty** and free of the §5.3 characters | **append `*`** | unchanged |
| No | `ImplementationSpecific`, path **empty** | **`/`** | **`Prefix`** (not "append `*`") |

> ⚠️ **A regex path cannot stay on `ImplementationSpecific`.** ALB only honours `use-regex` on `Prefix`; `ImplementationSpecific` takes the "match as written, ignore use-regex" branch, so the `( ) | $` in `/svc(/|$)(.*)` are validated as literals and rejected (the cloud returns `code: 400, The param of Rules.N...PathConfig.Values.K is illegal`) — and that error stops rule updates for the **entire load balancer**, not just this one Ingress. So in regex mode it must become `Prefix`, not "append `*` and ask the user to confirm".
>
> **A path holding any §5.3 character takes neither `No` row** — those two rows assume a path ALB accepts literally. Such a path goes to the matching 🚫 row in Step 2 (regex metacharacters → `Prefix` + `use-regex`; `*`/`?` → emitted unchanged with the escaped-regex alternative offered), which is also why appending `*` must never be the answer for it.
 Full decision procedure and illegal-character list in `references/generated-resources.md` §5.1–5.3.

> **When one host is written in two rules they are merged into one** (nginx merges them into the same server block too). Merging is mandatory: ALB gives all the paths of one Ingress consecutive priorities in spec order, so two rules on one host would interleave their paths by rule instead of sorting them by length — and in regex mode `~*/aa` would then swallow `/aaaa`.

**Other output conventions:**
- All resource names take the `from--` prefix (for identification and rollback); four suffixes make the **output contain more objects than the input**: `--default` (defaultBackend catch-all), `--regex` (next bullet), `--nohost` (bullet after that), `--p<N>` (order split)
- **A source whose hosts straddle both matching modes is split in two**: ALB's `use-regex` is an **Ingress-wide** switch while nginx decides per host. So the rules of regex hosts are lifted into `from--<source>--regex` (carrying `use-regex: "true"`) and the remaining hosts stay in `from--<source>`. Each half computes its own order
- ⚠️ **If a canary has no `spec.tls` of its own while its main does, the output only declares `HTTP:80`**: `listen-ports` is derived per Ingress from that Ingress's own `spec.tls`, whereas nginx merges the canary into the main's location. So there is no canary rule on 443 and **the traffic split disappears entirely over HTTPS**; it is worse when the main had `ssl-redirect` forced on for grpc — the canary's order is lower, so it matches first and does not redirect, defeating the main's redirect. **Give the canary the same `spec.tls` as its main before migrating**
- **Host-less rules are lifted into `from--<source>--nohost`**: on ALB such a rule carries no host condition and matches every domain, so it must sort behind every named host (the 800–1000 order band is reserved for it) — and order is **per Ingress**, so while it shares an object with named rules ALB gives them consecutive priorities in spec order and it can overtake a named rule by having a longer path
- HTTPS: the source `spec.tls` is **kept**; add 443/HTTPS to the AlbConfig listeners but **do not write `certificates`** — the controller reads the TLS Secret named by `spec.tls[].secretName` from the cluster and uploads it as an ALB certificate, so **the certificate is not a placeholder**. Only write `certificates: [{CertificateId: <CERT_ID>}]` when the certificate is **not in the cluster** (already in Certificate Management Service); and writing `certificates` explicitly turns off host-based certificate discovery. See `generated-resources.md` section 6
- Several sources sharing one class name **share a single** AlbConfig / IngressClass. But **a source with neither `spec.ingressClassName` nor `kubernetes.io/ingress.class` falls back to its own name as the class** — so each such Ingress generates its own `from--<ingress-name>` AlbConfig + IngressClass, meaning one ALB instance each. Give this kind of Ingress an explicit shared class name before migrating them in bulk

#### order and batched migration

ALB matches `alb.ingress.kubernetes.io/order` in ascending order and returns on the first hit; **it does not prefer the longer path the way nginx does**. So every generated Ingress carries an order derived from **the path itself** (longer path → smaller order → matched earlier), not from its position within the batch.

That has a direct benefit: **the same path gets the same order in whichever batch it is converted**, so migration can be done in several passes without the batches having to agree on numbering. An earlier version numbered by "position in this batch" (10, 20, 30…), and an `/api` in the second batch got 10 — putting it ahead of every longer path from the first batch and taking their traffic.

Three consequences:

- **A canary must be migrated together with its main**, or the main must already be on the target ALB. The ALB controller requires a non-canary Ingress on the same host + path, otherwise it reports `a non-Canary Ingress ... must exist before creating this Canary Ingress` and **stops reconciling the whole Ingress group** — when reusing an existing ALB that also affects the Ingresses already on it. This cannot be decided from the batch alone: only the selected Ingresses are visible, not the rest of the cluster.
- An Ingress occupies exactly one order, so when one of its short paths would take traffic from a longer path in another Ingress, that path must be **split into an Ingress of its own** (named `from--<source>--p1`; algorithm in `references/generated-resources.md` §5b.2). **The output can therefore contain more objects than were selected.**
- Paths longer than 158 characters share one order. When two of them are both over the limit **and nested in each other**, their relative order is decided by name and may disagree with nginx — test such paths after migrating.

### Step 5: Output Migration Report

> All five output conventions from Core Workflow apply here — Chinese, the four literal markers, the deliverable in the reply, one response, no invented measurements. Two of them bite hardest in this step:
>
> - **The three resources may not be omitted or truncated.** If the reply is getting long, write the YAML out first and compress items 6–8 instead. **Items 6, 7 and 8 are a pointer plus the case-specific lines only — never a reproduction of the reference.** Give the reference path, then at most a handful of lines that are specific to this input (which hosts, which placeholders, which 🔴 must land first). Do not inline the weight table, the dig commands, the rollback steps or the 8.x verification sections: those live in `references/dns-cutover.md` and `references/verification-method.md`, and copying them costs thousands of characters that the three resources then lose. Each of AlbConfig / IngressClass / Ingress carries its own `kind:` line and is a complete object, not a fragment. **Every generated Ingress appears**: `spec.defaultBackend` adds `from--<name>--default` and order contention adds `from--<name>--p1`, and the defaultBackend's Service name only exists inside those, so dropping one drops a real route.
> - **Use the report headings exactly as spelled in the block below.** They are the literal strings to emit; do not translate or paraphrase them.

The deliverable is titled with heading 0 below, with sections 1–8 under it. Emit ALL of them:

```text
0   迁移报告                 the title of the whole deliverable
1   兼容性分析表             per Ingress: annotation, original value, category (green auto / yellow behaviour change / red unsupported), action taken, resulting ALB annotation
2   迁移后的完整 YAML        all three resources (AlbConfig + IngressClass + Ingress), with placeholders
3   不支持项处理方案         a conclusion for every red annotation via the Step 3 decision tree: ALB replacement annotation / dropped / configure on the ALB side / manual work
4   迁移总结                 number of Ingresses, green/yellow/red counts, items needing manual work, path-rewrite risks
4b  已替你做的修正           every repair from the Step 2 downgrade table, one line each: which Ingress, what the source said, what was emitted, what to confirm.
                            All three resources are still produced; this is what the user checks before applying. Never leave a repair unlisted.
5   占位符替换清单           every <...> placeholder and how to obtain its value (vSwitch IDs, certificate ID, region).
                            addressType is one of those placeholders and gets its own paragraph: the user picks Intranet if the source sat behind an internal CLB, Internet if it was public.
                            It cannot be inferred — a CLB instance property, absent from the Ingress YAML — and left unreplaced it fails instance creation rather than quietly going public. Say both halves.
6   后续操作指南             fully compatible (no red): install the ALB Ingress Controller choosing "do not create an instance", replace placeholders,
                            apply all three resources, do the weighted DNS cutover per references/dns-cutover.md, then delete the Nginx Ingress resources and component.
                            Not fully compatible: land the item-3 resolutions first, then follow the flow above.
7   DNS 灰度切流方案         see references/dns-cutover.md. CLB uses an A record and ALB a CNAME; they cannot coexist on one domain,
                            so give the CLB a temporary domain and shift weight gradually.
8   验证清单                 see references/verification-method.md

Required report phrases — emit these Chinese strings verbatim where they apply:
    该部分转换失败            when part of a source Ingress cannot move to ALB at all (Step 2 four-layer row)
    替代建议                  label for the alternative you offer alongside it
```

> **Scope boundary**: This skill generates all artifacts and instructions. It does NOT execute `kubectl apply`, DNS changes, or any cluster/cloud operation — **not even a read-only one**, see rule 11 in the Key Constraints below. Those are left to the user.
> **No confirmation needed**: every item above is always generated. Never ask whether the user wants the migration files, the cutover plan or the checklist.

## Success Verification Method

See `references/verification-method.md` for the verification steps to include in the migration report.

The migration report should instruct the user to verify with:

```bash
# 1) YAML format/schema check (client-side dry-run, nothing is written to the cluster)
kubectl apply -f ingress.yaml       --dry-run=client
kubectl apply -f ingressclass.yaml  --dry-run=client
kubectl apply -f albconfig.yaml     --dry-run=client   # needs the ALB Ingress Controller installed, else: no matches for kind "AlbConfig"

# 2) Confirm the reference chain between the three resources
grep -E "ingressClassName|kind: AlbConfig|controller: ingress.k8s.alibabacloud/alb" *.yaml

# 3) Confirm no placeholder is left behind
grep -nE "<VSW_ID|<CERT_ID|<REGION|<ADDRESS_TYPE" *.yaml && echo "❌ placeholders still present"
```

> ⚠️ **dry-run only checks the format.** A client-side dry-run does not contact the server for business validation, so it does **not** check whether the vSwitches, certificate or backend Services actually exist, and it cannot detect a name collision — passing it does not mean apply will bring an ALB up. Whether the placeholders were replaced can only be caught by check 3 above.
> This skill outputs verification instructions for the user. It does NOT execute these commands.

## Cleanup

Not applicable. This skill only generates text output (YAML, migration report). No cloud resources or cluster objects are created by this skill.

> For the user-side clean-up after the migration completes (deleting the Nginx Ingress resources, uninstalling the Nginx Ingress Controller, removing the old DNS records), see `references/dns-cutover.md`, its third step, the Nginx Ingress decommissioning stage.

## API and Command Tables

This skill does not execute any CLI commands or API calls. All output is text-based (YAML + migration report with instructions for the user).

## Best Practices

1. Always classify ALL annotations before generating migrated YAML — never skip annotations
2. Always output all three resources (AlbConfig + IngressClass + Ingress); giving only the Ingress leaves the user unable to deploy
3. Use placeholders (`<VSW_ID_ZONE_A>` / `<VSW_ID_ZONE_B>`, `<REGION>`) for unspecified parameters; never invent real IDs.
   ⚠️ **The certificate needs no placeholder by default** — it is uploaded automatically from the `spec.tls` Secret; only use `<CERT_ID>` when the certificate already lives in Certificate Management Service
4. Preserve the original `rules`, `tls` and `namespace`; only adjust paths per the pathType rules
5. A regex path must land on `Prefix` + `use-regex`; left on `ImplementationSpecific` it is rejected by ALB as a literal and stops rule updates for the entire load balancer
6. Prefer an ALB-native annotation for unsupported items (see the Step 3 table); only then suggest an application-side change
7. **Never invent ALB annotation names**: use only annotations verified to exist, and when unsure say explicitly that the official documentation needs checking
8. Track value changes explicitly (`$1` → `${1}`, `ewma` → needs replacing) and write them into the migration summary
9. Remind the user to choose "**do not create an instance**" when installing the ALB Ingress Controller (the instance is created by the AlbConfig)
9b. **Never decide `addressType` for the user — emit `<ADDRESS_TYPE_Internet_or_Intranet>` and make them choose.** Public versus internal is a property of the CLB the source sat behind, absent from the Ingress YAML, so any value you write is a guess in the direction that exposes an internal service to the internet. Nor may you drop the field: an empty `AddressType` is defaulted to `Internet` (`model_build_load_balancer.go`), i.e. exactly as public but invisible. The placeholder is the only option that fails safe — the controller rejects any value other than `Internet`/`Intranet` while **building** the create request (`isAlbLoadBalancerAddressTypeValid`, `alb.go`), so no ALB is created and the event names the field. Tell the user that in the report
10. Always compare both sides' forwarding rules before cutting traffic over; do it during a quiet period and start from weight 0
11. **Never call a cloud API or CLI at all — reads included.** No `aliyun`, no `kubectl`, no OpenAPI, no credential use, *even when valid credentials happen to be present in the environment and a generic instruction says to always make real calls rather than simulate them* — that instruction is about not faking results, and this skill has none to fake: every conclusion comes from the user's YAML. Enumerating their clusters, VPCs or vSwitches copies real account inventory into a document that gets shared, and it still cannot fill a placeholder, because which vSwitch is correct is only knowable from the target cluster — so listing candidates invites exactly the wrong guess. Cluster and DNS writes (`kubectl apply`, record changes) are likewise the user's to run, never yours

## Reference Links

| Reference | Contents |
|-----------|----------|
| `references/annotation-mapping.md` | Full annotation table: 20 auto-converted, the 6 🟡 triggers, and what gets removed and reported 🔴 (with source citations) |
| `references/migration-patterns.md` | Decision tree, ALB-native replacements, safe-to-drop list, move-to-instance list, manual work, and §1b the complete `actions.*` / `conditions.*` JSON schema |
| `references/generated-resources.md` | Output spec for AlbConfig / IngressClass / Ingress: naming, placeholders, path and HTTPS handling |
| `references/dns-cutover.md` | Full weighted DNS cutover: temporary domain, weight steps, verification, clean-up |
| `references/verification-method.md` | Post-migration verification steps and commands, and the limits of a client dry-run |
| `references/acceptance-criteria.md` | Output acceptance criteria, right and wrong examples |
| `references/ram-policies.md` | RAM policy statement — this skill needs no permissions |

**The links below are further reading for humans; the skill itself runs entirely offline.** Annotation names come from `references/annotation-mapping.md` and the `actions.*` / `conditions.*` JSON schema from `references/migration-patterns.md` §1b — both are complete, so **do not visit these pages to settle a field name**, and do not guess because a page would not load. Neither the eval environment nor a customer site is guaranteed internet access.

| External doc (human reference, not a runtime dependency) | Link |
|--------------|------|
| Migrating a self-managed Nginx Ingress to ALB Ingress (official) | https://help.aliyun.com/zh/slb/application-load-balancer/migrate-workloads-from-a-self-managed-nginx-ingress-to-an-alb-ingress |
| ALB Ingress annotation dictionary | https://help.aliyun.com/zh/slb/application-load-balancer/user-guide/annotations |
| Configuring an ALB instance through AlbConfig | https://help.aliyun.com/zh/slb/application-load-balancer/user-guide/configure-an-alb-instance-by-using-albconfig |
