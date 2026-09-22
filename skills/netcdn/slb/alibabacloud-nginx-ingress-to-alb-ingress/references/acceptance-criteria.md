# Output acceptance criteria

Every output of this skill should meet the criteria below. Correct and incorrect examples included.

---

## 1. All three resources present

✅ **Correct**: AlbConfig + IngressClass + Ingress emitted together, with a self-consistent reference chain.

❌ **Wrong**: emitting only the converted Ingress.
> The user cannot deploy it — with no AlbConfig there is no ALB instance, and with no IngressClass nothing takes ownership.

❌ **Wrong**: generating one AlbConfig each for three Ingresses that share a class name.
> That creates three ALB instances: wasteful and billed. One class name **shares one set**.

---

## 2. Every annotation gets a conclusion

✅ **Correct**: every annotation in the input appears in the compatibility table, classified 🟢/🟡/🔴, and every 🔴 carries one of the four conclusions (replaced with an ALB annotation / dropped / must be configured on the ALB side / manual work required).

> **The scope is not limited to `nginx.ingress.kubernetes.io/*`**: `cert-manager.io/*`, `external-dns.*`, `nginx.org/*` and in-house `<domain>/*` keys are all reported 🔴 by the tool, and they belong in the table too. Only `alb.ingress.kubernetes.io/*` and the packaging / GitOps metadata prefixes are exempt.

❌ **Wrong**: describing every 🔴 as "this annotation has been removed".
> Reported and removed are two different sets: only six prefixes are kept out of the output (see `generated-resources.md` §4.1), and an in-house annotation reported 🔴 still stays on the object. Getting this backwards makes the user think the clean-up is done.

❌ **Wrong**: listing only the "supported" annotations in the table and not mentioning the rest.
> The user will assume the functionality is all there, and silently losing functionality is the biggest risk in a migration.

❌ **Wrong**: writing "unsupported, please handle it yourself" for a 🔴 and stopping there.
> A direction is mandatory. Look it up in `migration-patterns.md`.

---

## 3. Never invent ALB annotation names

✅ **Correct**: use only ALB annotations and JSON fields that appear in `annotation-mapping.md` (annotation names) or `migration-patterns.md` §1b (the complete `actions.*` / `conditions.*` schema). Those two files are the whole authority — **this skill is offline, so never fetch a doc page and never treat "I could not reach the documentation" as a reason to guess.** Not in either file ⇒ it does not exist ⇒ say "manual work required".

❌ **Wrong**: inventing `alb.ingress.kubernetes.io/auth-url` or `alb.ingress.kubernetes.io/session-cookie-name` to make the table look complete.
> Those annotations **do not exist**. After apply nothing happens and it is hard to diagnose. Better to say "manual work required".

---

## 4. Path and rewrite risks called out explicitly

✅ **Correct**: when the source is `ImplementationSpecific` and the host is in regex mode (any Ingress on that host carries `use-regex`/`rewrite-target`), emit `pathType: Prefix` + the path unchanged + `use-regex: "true"`, and explain why the pathType changed.

❌ **Wrong**: keeping `ImplementationSpecific` and appending `*`, producing `path: /svc(/|$)(.*)*`.
> ALB only honours `use-regex` on `Prefix`; `ImplementationSpecific` takes the "match as written, ignore use-regex" branch, so the `( ) | $` are validated as literals and rejected (measured: `code: 400, The param of Rules.N...PathConfig.Values.K is illegal`) — and rule updates then stop for **the entire load balancer**.
> A dry-run cannot catch this (it only checks format, not ALB semantics), so getting it right here is the only defence.

❌ **Wrong**: emitting a path holding `( ) [ ] { } | ^ $ \` as a **literal** (that is, on `Prefix`/`ImplementationSpecific` without `use-regex`).
> This is the one and only "better to emit nothing than write it this way" case: ALB's literal validation rejects these characters, and that error stops rule updates for **the entire load balancer**. The right move is to **add `use-regex: "true"` and put it on `Prefix`** for the user, and note under 🚫 that "this path is now handled as a regex; ALB's regex is case-sensitive, please verify" — not to refuse to produce output. See `generated-resources.md` §5.3.

❌ **Wrong**: refusing to produce anything and only reporting the reason when a 🚫 situation arises.
> 🚫 is a **downgrade**: all three resources are still emitted, whatever cannot be expressed faithfully is repaired per the downgrade table in SKILL.md Step 2, and every repair is listed under the 🚫 repairs section named in the SKILL.md Step 5 heading block. The user came for migrated YAML; handing back nothing means the skill ran for nothing.
> (The converter tool refusing those sources is correct — it feeds a console that applies YAML automatically, whereas the skill's output goes through human review.)

---

## 5. Placeholder conventions

✅ **Correct**: unknown parameters use `<VSW_ID_ZONE_A>` / `<VSW_ID_ZONE_B>` and `<REGION>`, with a placeholder list plus self-check commands at the end.

❌ **Wrong**: writing `certificates: [{CertificateId: <CERT_ID>}]` on the 443 listener.
> The certificate is **not a placeholder by default**: the controller reads the cluster Secret named by `spec.tls[].secretName` and uploads it automatically. Writing that block costs twice over — it leaves a placeholder the user has no way to fill, and it **turns off host-based certificate discovery**. Only write it when the certificate already lives in Certificate Management Service and not in the cluster. See `generated-resources.md` section 6.

❌ **Wrong**: inventing a realistic-looking `vsw-bp1abcdefg123456`.
> The user may apply it as-is, which either fails or points at the wrong resource.

❌ **Wrong**: asking "please provide your vSwitch ID" and stopping.
> Produce the complete result with placeholders instead.

---

## 6. No write operations

✅ **Correct**: output the `kubectl apply` / `dig` / DNS **commands** for the user to run.

❌ **Wrong**: actually calling `kubectl apply`, changing DNS, or creating an ALB.
> This skill's boundary is analysis and generation, not deployment.

---

## 7. Complete output in one response

✅ **Correct**: on receiving the YAML, output everything from Step 1→5 in a single response (compatibility table, YAML, plans for unsupported items, summary, placeholder list, next-steps guide, cutover plan, verification checklist).

❌ **Wrong**: "I have finished the annotation analysis. Would you like me to generate the migrated YAML?"
> Do not ask item by item; just produce it.

---

## 8. dry-run boundaries stated

✅ **Correct**: give the `apply --dry-run=client` command **only as a YAML format check**, and note that it validates neither the vSwitches, the certificate nor the backends, cannot detect a name collision, and that "passing ≠ an ALB will come up".

❌ **Wrong**: presenting a passing dry-run as "the configuration is fine".
> It only looks at format. An unreplaced placeholder, a nonexistent vSwitch, a name that collides with an existing object — dry-run waves all of them through.

---

## 9. The report is written in Chinese

✅ **Correct**: the analysis table, the summary and the guides are all in Chinese; code blocks (YAML / bash) keep their original syntax.

❌ **Wrong**: producing the report in English.

---

## Self-check list (run through it before answering)

- [ ] AlbConfig / IngressClass / Ingress all present, reference chain correct
- [ ] One AlbConfig / IngressClass per class name, not one per Ingress
- [ ] Every annotation in the input appears in the table (**including non-nginx prefixes**), and every 🔴 has a conclusion
- [ ] Every 🟡 is listed with what to confirm (6 trigger conditions in annotation-mapping.md §2; `limit-rps` and the regex case-sensitivity pair must say "must be measured")
- [ ] When the source wrote `ssl-redirect: "true"` and has a `spec.tls` block, the output keeps `alb.ingress.kubernetes.io/ssl-redirect` (independent of certificate coverage, see annotation-mapping.md §6.2)
- [ ] When the source **did not write** `ssl-redirect`, the output **does not have it either** (the sole exception is grpc forcing it on, which must be reported 🟡)
- [ ] Every 🚫 downgrade is listed under the 🚫 repairs section (heading 4b in the Step 5 block): which Ingress, what the source said, what was emitted, what to confirm
- [ ] All three resources are always produced — never "there was a 🚫 so nothing is given"
- [ ] Recipes needing `rule-direction.<svc>: Response` (`custom-http-errors`, `custom-headers`) do not omit the direction
- [ ] No unverified ALB annotation name appears anywhere
- [ ] On a regex-mode host: path unchanged + `pathType: Prefix` + `use-regex: "true"` (**not** keeping `ImplementationSpecific` and appending `*`)
- [ ] A path holding `( ) [ ] { } | ^ $ \` has `use-regex: "true"` added and sits on `Prefix`, never emitted as a literal
- [ ] Placeholders follow the convention, with a list and self-check commands attached
- [ ] `listen-ports` and the AlbConfig `listeners` **match exactly** (see the note below; a mismatch drags down the whole ALB)
- [ ] An Ingress with a `spec.tls` block has the 443 listener added (it applies to the whole Ingress regardless of which hosts are covered; the certificate does **not** need uploading by hand)
- [ ] The AlbConfig `listeners` hold no duplicate port + protocol combination
- [ ] `addressType` is left as `<ADDRESS_TYPE_Internet_or_Intranet>` — never resolved to `Internet`, never omitted — and the report gives the user both branches (`Intranet` for a source behind an internal CLB, `Internet` for a public one)
- [ ] The install instructions tell the user to choose "do not create an instance" for the ALB
- [ ] The DNS weighted-cutover plan and the rollback plan are attached
- [ ] No cluster or DNS write operation was performed

---

## Why the listeners must match exactly (measured)

The controller **will not** add a missing listener for you; it only validates. When an Ingress's `listen-ports` names a port + protocol the AlbConfig does not have, reconciliation fails outright:

```
Warning  FailedBuildModel  listener is not exist in <albconfig-name>, port: 443, protocol: HTTPS
```

**The blast radius is the whole ALB, not just this one Ingress** — the controller computes the union of required listeners per group, so one missing port stops **every** Ingress under that AlbConfig from reconciling (measured: a perfectly valid Ingress needing only 80 failed because another in the same group needed 8081). Already-published rules keep serving, but no further change can be pushed.

The reverse holds too: a **duplicate** port + protocol combination in the AlbConfig reports `duplicate listener for port %d and protocol %s in albconfig %s`, with the same consequence — the whole group fails to reconcile.

It heals once the listener is added: the Ingress shows `Normal / SuccessfullyReconciled` and `status.loadBalancer.ingress[0].hostname` is filled in with the ALB domain.
