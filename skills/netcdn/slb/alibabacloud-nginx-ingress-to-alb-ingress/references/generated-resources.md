# Migration output spec (AlbConfig + IngressClass + Ingress)

ALB Ingress needs **all three resources** to work; none is optional:

| Resource | Scope | Role |
|------|--------|------|
| `AlbConfig` | **Cluster** | Defines the ALB instance itself (edition, zones/vSwitches) and its listeners (port, protocol, certificate) |
| `IngressClass` | **Cluster** | Binds a class name to an AlbConfig and declares that the ALB controller owns it |
| `Ingress` | Namespace | The forwarding rules; points at the IngressClass through `spec.ingressClassName` |

Reference chain: `Ingress.spec.ingressClassName` → `IngressClass.metadata.name` → `IngressClass.spec.parameters.name` → `AlbConfig.metadata.name`

---

## 1. Naming conventions

| Object | Name | Example |
|------|------|------|
| AlbConfig | `from--<source class>` | `from--nginx` |
| IngressClass | `from--<source class>` (same as the AlbConfig) | `from--nginx` |
| Ingress | `from--<source Ingress>` | `from--nginx-web` |
| Ingress (defaultBackend catch-all) | `from--<source Ingress>--default` | `from--web--default` |
| Ingress (regex / literal split) | `from--<source Ingress>--regex` | `from--web--regex` |
| Ingress (host-less rules) | `from--<source Ingress>--nohost` | `from--web--nohost` |
| Ingress (order split) | `from--<source Ingress>--p<N>` | `from--web--p1` |

- The `from--` prefix makes the migration output easy to identify, lets it coexist with the original resources, and makes bulk clean-up on rollback simple.
- The last four suffixes make the **output contain more objects than the input**. When a name would exceed the apiserver's 253-character limit, the base is truncated and an 8-character digest is appended so two different names stay distinct.
- ⚠️ **Suffixes can collide**: if the same namespace already holds a source Ingress literally named `<someone-else>--default` (or `--regex` / `--nohost` / `--p1`), both would produce the same object name. The tool disambiguates with a numeric suffix and flags it 🚫 so the user can rename one and re-run for a stable name.
- **Several source Ingresses sharing a class name share one AlbConfig / IngressClass** (emit one copy). Do not generate a set per Ingress.
- ⚠️ **A source with neither `spec.ingressClassName` nor `kubernetes.io/ingress.class` falls back to its own name as the class** (source: `sourceIngressClass`). Each such Ingress then generates its own `from--<ingress-name>` AlbConfig + IngressClass — meaning **one ALB instance each**. Give this kind of Ingress an explicit shared class name before migrating them in bulk.

---

## 2. AlbConfig template

```yaml
apiVersion: alibabacloud.com/v1
kind: AlbConfig
metadata:
  name: from--nginx
spec:
  config:
    name: from--nginx
    edition: Standard              # only three literal values: Basic / Standard / StandardWithWaf
    addressType: <ADDRESS_TYPE_Internet_or_Intranet>   # ⚠️ the user picks; never ship a value — see section 7
    accessLogConfig: {}
    tags:
      - key: converted/ingress2albconfig
        value: "true"              # marks it as migration-tool output, for identification
    zoneMappings:
      - vSwitchId: <VSW_ID_ZONE_A> # ⚠️ must be replaced with a real vSwitch ID
      - vSwitchId: <VSW_ID_ZONE_B> # ⚠️ ALB requires at least two zones
  listeners:
    - port: 80
      protocol: HTTP
```

**Key points**
- `edition` accepts only the three literal values **`Basic` / `Standard` / `StandardWithWaf`** — to enable WAF write `StandardWithWaf`, not a descriptive phrase.
  ⚠️ **`Extensible` is a constant in the controller but AlbConfig explicitly does not support it**: the webhook rejects it and tells you to use the Gateway API `alb-extensible` GatewayClass instead. So an extensible-edition instance cannot go through this skill's three-resource path.
- `zoneMappings` needs **at least two** vSwitches in different zones; the placeholders `<VSW_ID_ZONE_A>` / `<VSW_ID_ZONE_B>` must be replaced with real vSwitch IDs in the same VPC.
- When installing the ALB Ingress Controller, choose "**do not create an instance**" — the instance is created by this AlbConfig, otherwise you end up with an extra idle one.
- A dry-run **does not** validate that a vSwitch exists (a placeholder passes too), so confirm it by hand.

---

## 3. IngressClass template

```yaml
apiVersion: networking.k8s.io/v1
kind: IngressClass
metadata:
  name: from--nginx
spec:
  controller: ingress.k8s.alibabacloud/alb    # fixed value, do not change
  parameters:
    apiGroup: alibabacloud.com
    kind: AlbConfig
    name: from--nginx                         # points at the AlbConfig above
```

> `controller` must be **exactly** `ingress.k8s.alibabacloud/alb`; get it wrong and the controller never takes ownership.

---

## 4. Ingress template

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: from--nginx-web
  namespace: default                                  # keep the source namespace
  annotations:
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80}]'
    # ... the converted alb.* annotations
spec:
  ingressClassName: from--nginx                       # points at the IngressClass
  rules:
    - host: www.example.net                           # keep the source host
      http:
        paths:
          - path: /svc
            pathType: Prefix                          # keep the source pathType
            backend:
              service:
                name: demo-svc
                port:
                  number: 80
  tls: []                                             # keep the source spec.tls
```

**Mandatory annotation**
- `alb.ingress.kubernetes.io/listen-ports`: must correspond to the AlbConfig `listeners`. With only 80 it is `'[{"HTTP":80}]'`; with HTTPS it is `'[{"HTTP":80},{"HTTPS":443}]'`.

### 4.1 Metadata inheritance rules

The output is a **new object**, not an edit of the source — the source Ingress keeps everything it had, and "dropped" below only means "not copied into the new object".

**Annotations**: everything is copied except the namespaces below (including the ones the tool reports as unsupported — reported and removed are two different sets).

| Prefix not copied | Reason |
|---|---|
| `nginx.ingress.kubernetes.io/`, `nginx.org/`, `nginx.com/`, `ingress.kubernetes.io/` | They configure a different ingress controller; ALB never reads them, and leaving them looks like configuration that still applies |
| `kubernetes.io/ingress.class` | Carried by `spec.ingressClassName` instead |
| `cert-manager.io/`, `external-dns.alpha.kubernetes.io/` | The source Ingress is still present during migration, so two Ingresses would fight over the same certificate Secret / DNS record |

⚠️ Dropping `cert-manager.io/*` means **the output will not renew the certificate**. It still references the same `spec.tls.secretName`, so HTTPS keeps working while the source Ingress exists; but **before deleting the source Ingress you must decide who renews that Secret**, otherwise HTTPS breaks when the certificate expires. See `dns-cutover.md` step three.

**Labels**: all copied, except the single key `ingress-controller` (whatever its value).

That label states "which ingress controller serves this", and since the output is served by ALB, inheriting it makes the claim false. The real cost is not untidiness but **accidental deletion**: the most natural clean-up at the end of a migration is `kubectl delete ing -l ingress-controller=nginx`, which would select the output too if it inherited the label.

Every other label (`team`, `env`, `app.kubernetes.io/*`, and a `kubernetes.io/ingress.class` written as a label) is **kept** — they are the user's own taxonomy, and deleting one is something no review step would catch.

> This label does not cause the nginx controller to reconcile the output. Ownership is decided only by `spec.ingressClassName` → IngressClass → `spec.controller`; labels play no part. Verified on a cluster: an Ingress whose `ingressClassName` points at ALB, labelled `ingress-controller: nginx`, produced the nginx controller log `ignoring ingress ... based on annotation : no object matching key "<albClass>" in local store`, with `ingress-controller` appearing 0 times in that same log, and the object's `status.loadBalancer` only ever held the ALB address.
>
> **A reusable diagnostic**: an Ingress claimed by nginx gets an NLB address, one claimed by ALB gets an ALB address — read `status.loadBalancer.ingress[].hostname` to see who owns the object.
>
> If the cluster marks nginx with a **different** key (say `lb-type: nginx`), that key **is** inherited, and a bulk delete by it would hit the output just the same.

---

## 5. Path and pathType conversion rules (the easiest thing to get wrong)

**Decide whether the host is in "regex mode" first, then decide how to write the path.** The order matters — the same source path produces completely different output in the two modes.

### 5.1 Deciding whether a host is in regex mode

nginx's rule: **within one source ingressClass**, if **any one** Ingress on a host uses `use-regex` or `rewrite-target`, then **every** path of **every** Ingress on that host is matched as a regex, regardless of their own pathType. So this is a **batch-level** decision that needs every Ingress being migrated in view:

```
For each Ingress in the batch:
  take its source ingressClass
    (spec.ingressClassName → the legacy kubernetes.io/ingress.class annotation → fall back to its own name)
  if use-regex is true
    (nginx uses strconv.ParseBool: true/True/TRUE/1/t/T count as true; on/yes do not — see ⚠️ below)
      → (that class, each of its rule.host) enters regex mode
  else if rewrite-target is present:
      → for each of its paths, if rewrite-target's value ≠ that path's value
        → (that class, that rule.host) enters regex mode
        (nginx exempts "the rewrite target is the path it sits on" — that rewrites nothing,
         so regex stays off)
```

> **Why it is keyed on "source ingressClass + host" and not on host alone**: nginx's regex modifier is decided per server block, and a server block belongs to **one** ingress controller. Two Ingresses under different ingressClasses are two independent servers even with a literally identical host, and use-regex on one does not taint the other. Keying on host alone would let a regex host under class A widen a same-named literal host under class B when the batch mixes source classes — the measured consequence being that `/Images` starts matching `/Imagesxyz` (the regex loses the segment boundary), while ALB's `~*` is case-sensitive where nginx's is not, so `/images/x` that used to be served now 404s.
>
> ⚠️ **`on` / `yes` are not truthy to nginx.** nginx parses these boolean annotations with `strconv.ParseBool`, so `on`/`yes` fail to parse → it falls back to the global default in the ConfigMap. Measured on a cluster (observed through ssl-redirect on a host with a certificate): `true` and `1` triggered a 308, while `on` and `yes` returned 200 (no effect). They pass nginx's admission webhook but **that does not mean they took effect**. So a boolean annotation written as `on`/`yes` must **not** be treated as true — such a value strips the annotation and is reported 🚫, see the downgrade table in SKILL.md Step 2.
>
> ⚠️ Only the Ingresses in this batch are visible. If another Ingress on the same class and host carries one of these annotations but was **not selected**, this decision cannot see it, and that host's matching will differ from what was expected after migration. Confirm that every Ingress on a host is in the batch before migrating.

### 5.2 Rewriting the path per mode

| Host in regex mode? | Source pathType | Output path | Output pathType | Extra |
|---|---|---|---|---|
| **Yes** | any, including `Exact` | **unchanged** | **`Prefix`** | stamp `use-regex: "true"` |
| No | `Prefix` | unchanged | `Prefix` | — |
| No | `Exact` | unchanged | `Exact` | — |
| No | `ImplementationSpecific` | **append `*`** | unchanged | — |
| No | `ImplementationSpecific` with an empty path | `/` | `Prefix` | — |

**Why regex mode must become `Prefix`**: ALB only honours `use-regex` on `Prefix`. The controller dispatches on pathType, and `ImplementationSpecific` takes the "return as written, ignore use-regex" branch — leave a regex path on `ImplementationSpecific` and ALB treats it as a literal plus wildcards. A source `Exact` has to become `Prefix` too: nginx is no longer treating it as an exact match at that point, so copying `Exact` across would be the unfaithful choice.

**Why `ImplementationSpecific` gets `*` appended outside regex mode**: ALB matches this pathType in full, so without the `*` only the path itself matches and every subpath falls through (measured: `/foo/x` against a bare `/foo` rule returns 503). With it appended the match is slightly wider than ALB's `Prefix` (`/foo*` also matches `/foobar`), and that is a deliberate choice: being too wide serves one extra request nginx would have refused, while being too narrow turns a request nginx was serving into a 404 — and in a migration the latter hurts more.

### 5.3 Path legality outside regex mode

When a host is **not** in regex mode nginx matches literally, and these characters in a path cannot be carried over as-is:

| Character | Why it cannot be waved through |
|---|---|
| `(` `)` `[` `]` `{` `}` `\|` `^` `$` `\` | ALB's literal path validation rejects them; the cloud returns **`code: 400, The param of Rules.N.RuleConditions.M.PathConfig.Values.K is illegal`**, and that error stops rule updates for the **entire load balancer** — see "Measured: how an illegal path freezes a whole ALB" below |
| `*` `?` | nginx matches them as ordinary characters while ALB matches them as wildcards, so the same path answers a different set of requests on each side |

> `.` and `+` are **not** on this list: they are common in ordinary paths (`/index.html`, `/a+b`) and ALB accepts them literally.

**What to do — the two rows need different repairs, and applying the first to the second changes the semantics.**

*Regex metacharacters* (`( ) [ ] { } | ^ $ \`): add `use-regex: "true"` for the user, put the path on `Prefix`, and report it 🚫 noting the path is now matched as a regex and ALB's regex is case-sensitive. The underlying cause is almost always "wrote a regex but forgot `use-regex: "true"`", so this is the repair the user would have made. **Never emit such a path as a literal** — that is the one case where producing nothing would be better, and adding use-regex avoids having to choose.

*`*` and `?`*: emit the path **unchanged** and report it 🚫, then offer `use-regex` **with the characters escaped** (`/a\*b`) as the faithful alternative. Do **not** simply add `use-regex` the way you would for the row above: as a regex, a bare `*` becomes a quantifier, so `/a*b` would start matching `/b` and `/aab` — a third meaning, different from both nginx's literal and ALB's wildcard. The user has to choose between ALB's wildcard and an escaped regex; that choice is theirs, not yours.

#### Measured: how an illegal path freezes a whole ALB (reproduced 2026-09)

A controlled experiment on an ALB already carrying three healthy Ingresses:

| Step | Observation |
|---|---|
| Baseline: create a **valid** Ingress on a new host | **200 after 55 seconds** — rules publish normally |
| Inject an Ingress with `pathType: ImplementationSpecific` and `path: /api/(.*)` | The cloud rejects it: `code: 400, The param of Rules.1.RuleConditions.2.PathConfig.Values.1 is illegal` |
| Create another **valid** Ingress (a different new host) | **Still 503 after 190 seconds** — the rule can never be pushed |
| Meanwhile, request the **pre-existing** hosts | **200 throughout** — already-published rules keep serving and are not withdrawn |
| Delete the illegal Ingress | **50 seconds later** the stuck valid Ingress turns 200 — it heals |

**So "frozen" means precisely: already-published rules keep serving, but no rule change on that ALB (addition or modification) takes effect any more.** That is especially dangerous in a migration — when reusing an ALB already carrying production traffic, one illegal path stops **every other Ingress in the batch** from going live while the existing traffic looks perfectly healthy, so nothing shows it unless you read the events.

**A diagnostic (measured)**: the `FailedApplyModel` event for this error is copied, with the **same requestId**, onto **every** Ingress on that ALB and onto the AlbConfig object. So seeing `FailedApplyModel` on your own Ingress with a path in the message that is **not yours** means someone else's illegal configuration on the same ALB is holding you up — use the path in the message to find the real source Ingress.

---

## 5b. Computing the order (ALB does not prefer the longer path)

ALB matches `alb.ingress.kubernetes.io/order` in ascending order and **returns on the first hit**. It does not prefer the longer path the way nginx does, so every generated Ingress **must** carry an order; without it the controller gives them all the default of 10 and breaks ties by name — swapping "the more specific rule wins" for alphabetical order.

### 5b.1 The formula

The order is derived from **the path itself**, not from its position in the batch. Note it is computed on the **output path from 5.2**, not the source path:

```
order for one path (length taken from the output path, but the trailing *
appended for ImplementationSpecific does not count):
    named host   →  800 - min(path length, 158) × 5
    no host      → 1000 - min(path length,  39) × 5     ← nginx's default server
    if the **post-5.2** pathType is Exact, subtract 1 more
        ← note: the output, not the source. In regex mode a source Exact has already
          become Prefix, and then **nothing is subtracted** — nginx is not treating it
          as an exact match at that point either. Judging by the source pathType would
          be off by one for the whole row.
order of an Ingress = the **minimum** over all its paths (it can only hold one position)
if the Ingress is a canary, subtract 2 more
finally clamp to [1, 1000]
```

The length comes from the **output** path, but the `*` appended for `ImplementationSpecific` is stripped first (source: `strings.TrimSuffix(s.match, "*")` in `order.go`), so that family works out the same length as the source. **The only case where it differs from the source** is the last row of 5.2: a source `ImplementationSpecific` with an empty path becomes `/`, counted as length 1 → `795`, not the `800` the source length of 0 would give.

Because it depends only on the path, **the same path gets the same order in whichever batch it is converted**, which is what makes migrating in several passes possible. An earlier version numbered by "position in this batch" (10, 20, 30, …), and an `/api` in the second batch took 10 — putting it ahead of every longer path from the first batch and stealing their traffic.

### 5b.2 Two consequences to watch

**A canary must be migrated in the same batch as its main Ingress.** A canary sits two slots ahead of its own path's order so it matches before the main. But the ALB controller also insists on a **non-canary** Ingress existing on the same host + path, otherwise it reports `a non-Canary Ingress ... must exist before creating this Canary Ingress` and **stops reconciling the whole Ingress group** — which, when reusing an existing ALB, also affects the Ingresses already on it.

**Within one Ingress, sorting does the work rather than splitting — but merge same-host rules before sorting.** The order only decides the sequence *between* Ingresses; ALB's rule priority is `(Ingresses sorted by order) × (their rules) × (the rule's paths)` **flattened and numbered from 1 upwards**, so the sequence *within* one Ingress **is the spec order in the output YAML**, which is directly under our control. Hence in the output:

- **When one host is written across several rules, merge them into one first** (nginx merges them into the same server block too). Without merging, the flattened paths interleave by rule instead of sorting by length — and in regex mode `~*/aa` would then swallow an `/aaaa` from another rule on the same host.
- Within one rule, sort the paths by **descending path length**.
- Between rules, sort by each rule's **longest** path, descending (comparing by the shortest sorts them backwards, which is the other half of the interleaving problem above).

After merging, every path of one host sits in a single rule in descending length order — that is the equivalent of nginx's "longest first" on ALB's "first match wins" model. Different hosts never compete, so their relative order does not matter.

**The one thing that must be split out of a source is host-less rules.** On ALB such a rule carries no host condition and matches every domain, so it must sort behind every named host; and order is **per Ingress**, so while it shares an object with named rules the flattened sequence is decided by path length alone and it can overtake a named rule. Host-less rules are therefore lifted into `from--<source>--nohost`, where the 5b.1 formula gives them an order in the 1000 band, stably behind the named ones.

> A known narrow edge: sorting compares length only, so an `Exact` and a `Prefix` of **the same length within one Ingress** (say `Exact /foo` and `Prefix /foo`) cannot be told apart and are decided by the order in the source YAML. Across Ingresses the "subtract 1 for Exact" rule handles it; within one Ingress it does not. The surface is narrow — measure it if you hit it.

**An Ingress holds exactly one order, so its short paths get dragged forward.** (This only happens **between** Ingresses.) When one Ingress's short path would steal traffic from a longer path in another Ingress, that short path must be **split into an Ingress of its own** (named `from--<source>--p1`) to reach the position it deserves. The criterion:

```
path p belongs to Ingress X, path q to Ingress Y (X ≠ Y), and:
    order(X) < order(Y)          ← p currently sorts ahead of q
    p's own order > q's          ← but p is shorter and should sort behind q
    p and q could match one request  ← the hosts intersect and q falls inside p's prefix
  ⇒ p must be split out
```

**Splitting has to be repeated to a fixed point**, because lifting a path moves it later, which can leave a third path that was safely behind it now misplaced:

```
repeat:
  scan for every misplaced path using the criterion above
  if none → done
  lift each misplaced path into a new Ingress:
      name     from--<source Ingress>--p1, --p2, … (consecutive per source; never reuse a
               number across rounds)
      content  copy the parent's annotations, tls and ingressClassName; keep only this path in rules
      order    recomputed from its own path (it now holds an Ingress alone, so the order is its own band)
      and remove that path from the parent's rules
  recompute the parent's order from the paths that remain
```

The numbering must stay consecutive across rounds: if the same source has one path lifted in round 1 and another in round 2 and both start at `--p1`, two objects end up with the same name. Likewise, when a source is split into a "regex half" and a "literal half" by 5.1, the split numbering has to run across both halves — their names all derive from the same source name.

> Several paths on **the same host** do **not** need splitting: ALB expands them into consecutive priorities in spec order. Only two things need splitting — preemption across Ingresses (this section) and host-less rules (above).

> Paths longer than 158 characters share one order. When two of them are both over the limit **and nested in each other**, their relative order is decided by name and may disagree with nginx — measure such paths after migrating.

---

## 6. HTTPS / certificate handling

When the source Ingress has `spec.tls`:
1. **Keep `spec.tls` on the migrated Ingress** — that is where the certificate comes from, see below;
2. Add a 443/HTTPS listener to the AlbConfig `listeners`:

```yaml
  listeners:
    - port: 80
      protocol: HTTP
    - port: 443
      protocol: HTTPS
      # no certificates needed: the certificate comes from the Ingress's spec.tls, see below
```
3. Update the Ingress's `listen-ports` to `'[{"HTTP":80},{"HTTPS":443}]'` to match.

### The certificate does not need uploading by hand

**The ALB Ingress Controller uses the Kubernetes TLS Secret directly**: it reads the Secret named by the Ingress's `spec.tls[].secretName` from the same namespace, takes `tls.crt` / `tls.key`, uploads them as an ALB certificate named `<namespace>-<secret>-<digest>`, and attaches it to the HTTPS listener. So as long as the source's `spec.tls` is kept intact, **the certificate is already there — nothing needs uploading to Certificate Management Service first, and no `<CERT_ID>` placeholder is needed**.

> Basis: `cloud-provider-alibaba-cloud/pkg/controller/ingress/reconcile/builder/albconfig_manager/model_builder.go:310` (iterates `ing.Spec.TLS` and calls `buildSecretCertificate` for each `secretName`) and `model_build_certificate.go:28-50` (reads the Secret's `tls.crt`/`tls.key` and derives the certificate name).

When you *do* need `certificates: [{CertificateId: ...}]`: when the certificate is **not in the cluster** but already uploaded to Certificate Management Service. Both sources can coexist and the controller merges them; but note that **writing `certificates` explicitly in the AlbConfig turns off host-based automatic discovery**.

### When a 443 listener is needed

The criterion is **whether the Ingress has any `spec.tls` block** — not which hosts the certificate covers. Verified on a cluster: nginx serves 443 and honours `ssl-redirect` for every host of such an Ingress, including a host no certificate covers (see `annotation-mapping.md` §6.2 for the four probe results).

| Source shape | 443 needed? |
|---|---|
| Any `spec.tls` block at all, whatever its `hosts` says — exact, wildcard, unrelated, or empty | ✅ |
| No `spec.tls` block | ❌ this Ingress is plain HTTP |

An earlier version of this document decided per rule host, matching `spec.tls[].hosts` against the rule's host with wildcard rules. That model was refuted by measurement: it under-created the listener, so an Ingress whose `tls.hosts` matched no rule host got a redirect pointing at a 443 that was never created.

The failure mode for a missing 443 is subtle: `spec.tls` is there, the certificate looks configured, but the listener does not exist, HTTPS never works, **and nothing reports an error**.

> ℹ️ With a wildcard certificate you will see a `Normal / MismatchHost` event, reading something like `mismatchTlsHostsIngress: [a.example.com]`. **For this tool's output that is normal and does not affect HTTPS**, but the reason has two layers and stopping at the first one leads to a wrong conclusion:
>
> 1. The certificate is uploaded from `spec.tls` and attached to the listener **unconditionally** (`model_builder.go:305-318` iterates `ing.Spec.TLS` with no host matching), so the certificate is definitely present.
> 2. **But "does the rule land on 80 or 443" is a separate question, and the two are mutually exclusive.** `withTlsRule` decides which listener a rule belongs on using an **exact** match, `contains(tls.Hosts, host)` (`model_build_listener_rules.go:220-235`): an exact hit → 443 only; no match (a wildcard, or an empty `hosts`) → 80 only. By that logic a wildcard certificate's host rules would **not** appear on 443 at all, and HTTPS would not work.
>
> What saves it is a third point: that gate **is skipped entirely** as long as the Ingress carries the `alb.ingress.kubernetes.io/listen-ports` annotation (or `ssl-redirect: "true"`) — see `forceListenIngress` (`model_build_listener_rules.go:237-243`) and its caller `if rule.Host != "" && !forceListenIngress(ing)` (:145). This tool **writes `listen-ports` on every output**, so the output takes the "attach to every port declared in listen-ports" path and neither wildcards nor an empty `hosts` matter.
>
> 🚨 **Which gives a hard constraint: never remove `listen-ports` from a generated Ingress.** It is not merely "keep it aligned with the AlbConfig listeners" (section 4) — it is also the switch that decides whether HTTPS works at all. A hand-written or hand-edited ALB Ingress **without** `listen-ports` and using a wildcard certificate looks fine (the certificate is attached, the 443 listener exists) but its rules only sit on 80, and HTTPS is silently unavailable.

---

## 7. Placeholder list (all must be replaced)

| Placeholder | Meaning | How to obtain it |
|--------|------|---------|
| `<VSW_ID_ZONE_A>` / `<VSW_ID_ZONE_B>` | vSwitch IDs in two different zones | The VPC console; must be in the same VPC as the cluster |
| `<REGION>` | Region ID | e.g. `cn-hangzhou` |

The HTTPS certificate is **not a placeholder** — it comes from the Ingress's `spec.tls`, see section 6.

> ⚠️ **`addressType` is a placeholder — `<ADDRESS_TYPE_Internet_or_Intranet>` — and it is the one placeholder whose whole purpose is to block the apply.** Public versus internal **cannot be inferred**: it is a property of the CLB instance the source Ingress sat behind, absent from the Ingress YAML, and this skill has no cloud permission to read it (nor may it acquire one). So there are only three things the output could do, and two of them are unsafe:
>
> | What the output does | What happens |
> |---|---|
> | Omit the field | An empty `AddressType` is **defaulted to `Internet`** (`model_build_load_balancer.go`: `if lbModel.AddressType == "" { … LoadBalancerAddressTypeInternet }`). Public, and invisibly so — nobody notices an absent field |
> | Write `Internet` | Public, this time visibly. Still a guess, and a user who applies without reading the report exposes an internal service |
> | **Write the placeholder** | `isAlbLoadBalancerAddressTypeValid` (`alb.go`) accepts only `Internet`/`Intranet`, and it is checked in `buildSDKCreateAlbLoadBalancerRequest` — i.e. **while assembling the create request, before the cloud API is called**. Reconcile fails with `invalid load balancer address type: <ADDRESS_TYPE_Internet_or_Intranet>`, **no ALB is created**, and the event names the field |
>
> The placeholder costs nothing: `zoneMappings` already ships `<VSW_ID_ZONE_A>`/`<VSW_ID_ZONE_B>`, so this AlbConfig can never be applied unedited anyway. Making `addressType` a placeholder simply moves the public-versus-internal decision into the edit the user is already forced to make, and the existing pre-apply placeholder grep catches it for free. Note that the CRD carries `x-kubernetes-preserve-unknown-fields`, so a client-side dry-run **passes** — the block lands at reconcile, which is why the report must tell the user to read the events after applying.
>
> (Incidentally, `ipv6AddressType` defaults the other way — absent means `Intranet`.)

Attach a self-check command at the end of the migration report:
```bash
grep -nE "<VSW_ID|<REGION" *.yaml && echo "❌ placeholders still present — do not apply"
```

> Placeholders **pass every automated check**: the AlbConfig CRD is `x-kubernetes-preserve-unknown-fields` with no structural schema, and measurement showed it does not even validate field types (writing a listener as `{"port":"not-a-port","protocol":123}` passes), while dry-run waves an AlbConfig holding `vsw-xxx` straight through. So the grep above is the only defence; do not count on apply catching it.

---

## 8. Apply order

Deploy in dependency order:

```bash
kubectl apply -f albconfig.yaml      # 1. create the instance first
kubectl apply -f ingressclass.yaml   # 2. then bind the class name
kubectl apply -f ingress.yaml        # 3. finally the forwarding rules
```

After apply, take the ALB domain for the DNS cutover:
```bash
kubectl get albconfig                # read the DNSNAME column
```

> ⚠️ apply **really creates an ALB instance and starts billing**, unlike a dry-run.
