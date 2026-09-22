# Nginx → ALB Ingress annotation lookup table

This is the **authoritative** table. Its contents come from the source of the official ALB migration tool `ingress2albconfig`, cross-checked against the ALB Ingress Controller source.

- 🟢 **Auto-converted (20)**: rewritten to the matching ALB annotation — per `pkg/i2alb/providers/ingressnginx/feature_*.go` (`AddInfo`)
- 🟡 **Behaviour change (6 trigger conditions, see §2)**: converted, but the semantics may differ and need human confirmation — same source (`AddError`)
- 🔴 **Unsupported (= the ones that get removed, not limited to the nginx prefix)**: what `feature_not_support.go` (`AddCritical`) reports is exactly what it deletes — `nginx.ingress.kubernetes.io/`, `nginx.org/`, `nginx.com/`, `ingress.kubernetes.io/` (they configure a different ingress controller) plus `cert-manager.io/`, `external-dns.alpha.kubernetes.io/` (they would fight the source Ingress over the same resource during migration). A newly added upstream nginx annotation is therefore reported too — **nothing is silently ignored**
- Every other unconsumed annotation (in-house `<domain>/*`, `prometheus.io/*`, …) is **copied verbatim and reported 🟢 carried over**; packaging / GitOps metadata prefixes (`kubectl.kubernetes.io/`, `app.kubernetes.io/`, `helm.sh/`, `meta.helm.sh/`, `argocd.argoproj.io/`, `fluxcd.io/`, `kustomize.toolkit.fluxcd.io/`) are neither reported nor removed

> ⚠️ What is reported 🔴 and what is removed are now **the same set**, deliberately: calling an annotation that stays on the object "unsupported" is untrue, and any single 🔴 pushes the whole batch to `PartialSuccess`. Full prefix list in `generated-resources.md` §4.1.
>
> ⚠️ **One annotation can appear in both 🟢 and 🟡.** `rewrite-target` does exactly that once regex applies: 🟢 (→ `rewrite-target`) plus 🟡 (→ `use-regex`). Report both.

> ⚠️ Where this table shows `actions.<svc>` / `conditions.<svc>`, **the suffix must be the Service name referenced by that path in `spec.rules`** — not the type of the action or condition (the type goes in the JSON `type` field). Write `actions.redirect` with no service of that name in rules and the annotation is never read, with no error either. Spelling and the full type list are in `migration-patterns.md`, Level 1.

> Prefix convention: the nginx side is always `nginx.ingress.kubernetes.io/` and the ALB side always `alb.ingress.kubernetes.io/`; both are omitted in the tables.

---

## 1. 🟢 Auto-converted (20)

| # | nginx annotation | ALB annotation | Key changes? | Additional behaviour |
|---|-----------|---------|-------------|---------|
| 1 | `canary` | `canary` | — | The order is derived from the path length and then moved two slots earlier — **not** a fixed `"9"` (a fixed value lets a canary steal traffic from a longer path; measured) |
| 2 | `canary-by-header` | `canary-by-header` | — | |
| 3 | `canary-by-header-value` | `canary-by-header-value` | — | |
| 4 | `canary-by-cookie` | `canary-by-cookie` | — | |
| 5 | `canary-weight` | `canary-weight` | — | The value is scaled to a percentage using `canary-weight-total` (item 20); a non-integer, a negative, or a total ≤ 0 → dropped and reported 🔴. ⚠️ **Reported 🟡 when it appears together with `canary-by-cookie`/`canary-by-header`** (§2 trigger 5): nginx allows the combination, ALB's semantics differ, so the user must pick weight *or* header/cookie |
| 6 | `enable-cors` | `enable-cors` | — | |
| 7 | `cors-allow-origin` | `cors-allow-origin` | — | |
| 8 | `cors-allow-methods` | `cors-allow-methods` | — | |
| 9 | `cors-allow-headers` | `cors-allow-headers` | — | |
| 10 | `cors-expose-headers` | `cors-expose-headers` | — | |
| 11 | `cors-allow-credentials` | `cors-allow-credentials` | — | |
| 12 | `cors-max-age` | `cors-max-age` | — | Absent from the official documentation table, but the tool supports it. ⚠️ **ALB only accepts -1..172800 and nginx's own default of 1728000 is exactly 10x that maximum**: above the maximum → clamped to `172800` and reported 🟡 (shorter preflight cache); non-integer or < -1 → dropped and reported 🔴. Copying an over-limit value makes ALB answer `The param of 1728000 is illegal` and **freeze rule updates for the entire load balancer** |
| 13 | `backend-protocol` | `backend-protocol` | — | ⚠️ **The value must be converted**: nginx uses upper case (`HTTPS`/`GRPC`), ALB only accepts lower case (`https`/`grpc`). See §3. **Reported 🟡 for `GRPCS`** (§2 trigger 4): ALB has no `grpcs`, so it is downgraded to `grpc` and no longer speaks TLS to the backend; also **🟡 when `grpc` forces `ssl-redirect` on** a source that was not redirecting |
| 14 | `load-balance` | **`backend-scheduler`** | ✅ changes | Only `round_robin`→`wrr` (plus the tolerated `least_conn`→`wlc`, `ip_hash`→`sch`); **`ewma` has no counterpart → 🔴**, see §3. ⚠️ **Reported 🟡 when `upstream-hash-by` was converted to `uch` and this asked for something else** (§2 trigger 6): ALB has a single scheduler field, so the consistent hash **overrides** it |
| 15 | `upstream-hash-by` | **`backend-scheduler-uch-value`** + `backend-scheduler: uch` | ✅ changes | ⚠️ **Only `$arg_<name>` converts** (taking `<name>`); other nginx variables → 🔴, see §3 |
| 16 | `ssl-redirect` | `ssl-redirect` | — | It applies when "this Ingress has a `spec.tls` block", regardless of certificate coverage (§6.2). ⚠️ **Do not add it when the source did not write it**: the implicit default comes from the controller ConfigMap and ACK ships it as `false` (measured, §6.2), so inventing it turns plaintext traffic into a 308. With no `tls:` block it is dropped |
| 17 | `use-regex` | `use-regex` | ✅ changes | **Reported 🟡 whenever the output ends up matched by regex**: ALB's regex is case-**sensitive** while nginx's `~*` is not (measured: with regex in effect nginx serves `/images/x` from a `/Images` rule, ALB answers 503). Tainting details in §6.1; when the value is false and no neighbour taints the host, it is reported 🟢 with an empty target (ALB needs no annotation to match literally) |
| 18 | `rewrite-target` | `rewrite-target` | — | `$N` → `${N}`. A value holding an nginx variable (`$request_uri`, `$args`, …) or a `?` **cannot be expressed by ALB, so the annotation is dropped and reported 🔴** (the route still converts, it just no longer rewrites the path). ⚠️ **Otherwise this annotation yields two rows, not one**: the rewrite itself is 🟢, and because its presence puts the host into regex mode it is **also reported 🟡** keyed `rewrite-target` → `alb.../use-regex` (ALB's regex is case-sensitive, nginx's `~*` is not). Reporting only the 🟢 hides the case-sensitivity risk. The sole exception is a value equal to the path it sits on — nginx rewrites nothing and does not enable regex, so no 🟡. Tainting details in §6.1 |
| 19 | `limit-rps` | **`traffic-limit-ip-qps`** | ✅ changes | **Always reported 🟡** (§2 trigger 1 — that path only ever calls `AddError`, never `AddInfo`). Both mean "per client IP per second". ⚠️ **The same number lets very different traffic through**: nginx counts per replica and allows a 5x burst by default, ALB counts once with no burst; and this tool emits one rule per path, each counting independently, where nginx has one counter per Ingress. A value outside ALB's 1–100000 means the annotation is dropped and reported 🔴 |
| 20 | `canary-weight-total` | **folded into `canary-weight`** | ✅ changes | ALB reads `canary-weight` with no denominator (`getIfOnlyWeight` is a bare `Atoi`), so the total has to be folded in here: `50/1000` is 5% on nginx and copying it verbatim means 50% on ALB. A share that does not divide evenly is rounded and reported 🟡; on its own (with no `canary-weight`) it is not consumed and is still reported 🔴 |

**Additional handling (not under the `nginx.ingress.kubernetes.io/*` prefix):**

| nginx annotation | Handling | Note |
|-----------|------|------|
| `kubernetes.io/ingress.class` | Dropped; there is no ALB annotation for it | The class name is carried by `spec.ingressClassName` instead |

---

## 2. 🟡 Behaviour change (conditionally triggered)

The **six reachable trigger conditions** for `AddError` in the source, each mapped to its `feature_*.go`:

| # | Trigger | Reported on which annotation | Why | Recommended action |
|---|---------|---------------|------|---------|
| 1 | `limit-rps` has a legal value (1..100000) | `limit-rps` → `traffic-limit-ip-qps` | **Unconditional** — that path in `feature_limit.go` only has `AddError`, never `AddInfo` | Measure the allowed throughput: nginx counts per replica and allows a 5x burst by default, ALB counts once with no burst |
| 2 | The output ends up matched by regex | `use-regex` → `use-regex`; if the regex was pulled in by `rewrite-target`, it is reported on `rewrite-target` → `use-regex` | Two axes differ, not one: ALB's regex is **case-sensitive** where nginx's `~*` is not (measured), and **whether ALB anchors the pattern is unverified** while an nginx `~*` location *searches* | Check every path with mixed case, **and measure anchoring** — see the note below |

> ⚠️ **Anchoring is a second, independent difference and it is NOT measured.** An nginx `~*` location matches if the pattern is found **anywhere** in the URI, so `/api/v[0-9]+/.*` also serves `/prefix/api/v1/users`. If ALB instead requires the pattern to span the whole path, that request stops matching after migration — a silent 404/503 on a route that worked. We have measured case-sensitivity and have **not** measured this, so do not state either behaviour as fact: list it alongside case-sensitivity as something the user must verify with real URLs before shifting weight. In particular, do not reason from an offline `re.fullmatch` experiment and present the result as ALB's behaviour.
| 3 | `cors-max-age` exceeded ALB's maximum and was **clamped** to 172800 | `cors-max-age` → `cors-max-age` | nginx's default of 1728000 is exactly 10x the maximum, so this is easy to hit | Confirm a shorter preflight cache is acceptable |
| 4 | `backend-protocol: GRPCS` | `backend-protocol` → `backend-protocol` | ALB has no `grpcs`, so it is downgraded to `grpc` | Confirm the backend TLS semantics: after the downgrade ALB no longer speaks TLS to the backend |
| 5 | `canary-weight` appears **together with** `canary-by-cookie` / `canary-by-header` | `canary-weight` → `canary-weight` | nginx allows the combination, ALB's semantics differ, and there is no equivalent mapping | Confirm the intent with a human: by weight or by header/cookie — **pick one** |
| 6 | `upstream-hash-by` converted to `uch` while `load-balance` also has a value that is not `uch` | `load-balance` → `backend-scheduler` | ALB has a single scheduler field, so the consistent hash **overrides** whatever `load-balance` asked for | Confirm the consistent hash is what is wanted; to keep `load-balance`'s algorithm, remove `upstream-hash-by` |

> There used to be a seventh: `ssl-redirect` where some hosts were not covered by the certificate. Cluster measurement proved nginx redirects those hosts too, so both sides agree and **that 🟡 was a false alarm**. It was removed along with the §6.2 correction.

> Note: the tool produces no `mock` ("approximate") verdict — `pkg/output/message.go` has only `AddCritical` / `AddError` / `AddInfo`, no `AddWarning`. So only 🟢 / 🟡 / 🔴 ever appear.
>
> ⚠️ **A non-boolean value for a boolean annotation is not in this table** — it is not 🟡 but a 🚫 downgrade: the annotation is stripped, the rest of the Ingress is still emitted, and the original value is reported so the user can fix it. `converter.go` runs `validateBooleanAnnotations` ahead of every feature, which is why the `AddError` branches for non-boolean values inside `feature_canary.go` / `feature_cors.go` / `feature_redirect.go` are unreachable. See the downgrade table in SKILL.md Step 2.

---

## 3. Values that must change

| Annotation | Change | Why |
|------|------|------|
| `rewrite-target` | `/$2` → `/${2}` | ALB's capture-group syntax is `${N}` |
| `backend-protocol: HTTPS` | → `https` (**lower-cased**) | ALB matches this annotation **case-sensitively and exactly**, accepting only `https`/`grpc`; an upper-case value falls to the default branch → **the backend is silently downgraded to cleartext HTTP**. The tool converts it automatically, marks values with no counterpart (`AUTO_HTTP`/`FCGI`) red and `GRPCS` yellow |
| `load-balance: ewma` | 🔴 not converted | ALB's scheduling algorithms are only `wrr`/`wlc`/`sch`/`uch` — **no EWMA**. The tool marks it red and asks for a human choice rather than dropping it silently |
| `upstream-hash-by: $request_uri` and friends | 🔴 not converted | **ALB's consistent hash is fixed to hashing a query-string parameter** (source: `ServerGroupSchedulerUchType = "QueryString"`), and `uch-value` is the **parameter name**. So only nginx's `$arg_<name>` converts (→ `uch-value: <name>` with `backend-scheduler: uch` set at the same time); `$request_uri` / `$remote_addr` and the like cannot be expressed and are marked red |

---

## 4. 🔴 Unsupported (a catch-all verdict)

**How it is decided**: the tool maintains **no "unsupported list"**. Every feature that converts something deletes the annotation it consumed, so whatever is left at the end of the pipeline is unhandled → marked 🔴 with a `reason`. **The scope is not limited to the nginx prefix**; only `alb.ingress.kubernetes.io/*` and the packaging / GitOps metadata prefixes are exempt (see the top of this document).

The benefit: **completeness holds by construction**. When ingress-nginx adds an annotation in future it is reported automatically rather than dropped silently for being "off the list". (The old implementation used a hardcoded list of 74, which left **38** of the 130 upstream annotations outside both lists and silently dropped — including `proxy-body-size`, `enable-modsecurity`, `ssl-ciphers` and `x-forwarded-prefix`.)

⚠️ **Whether a 🔴 annotation stays on the output depends on its prefix, not on the verdict.** `nginx.ingress.kubernetes.io/*` is in `droppedAnnotationPrefixes` and is **never copied over** (measured: a source `proxy-body-size` is reported 🔴 and is absent from the output) — leaving it would suggest the setting still applies, and the self-check in `verification-method.md` is written around "no nginx annotation should appear in the output". An in-house prefix such as `mycompany.com/*` is still copied verbatim even when reported 🔴. Full prefix list in `generated-resources.md` §4.1.

The capability domains below give the direction for each. **All 130 upstream annotations are named individually** (the baseline is ingress-nginx's own `docs/user-guide/nginx-configuration/annotations.md`), so an annotation not found here should be a newer upstream addition — infer from the direction of its capability domain, report it 🔴 per the catch-all rule above, and see `migration-patterns.md` for the full resolution.

> The subsections **deliberately carry no counts**: counts drift as upstream adds and removes annotations, and they are the easiest thing to forget to update (this document has historically said 21 while listing 25, and 2 while listing 3). To check for a gap, diff against the full baseline rather than trusting a number in parentheses.

### 4.1 Canary extras
| Annotation | Direction |
|------|---------|
| `canary-by-header-pattern` | Manual work (ALB's canary matches a header value exactly) |
| ~~`canary-weight-total`~~ | **Auto-converted** (folded into `canary-weight`, see §1 item 20) — does not walk this tree |

### 4.2 Session persistence
`affinity`, `affinity-mode`, `affinity-canary-behavior`, `session-cookie-name`, `session-cookie-path`, `session-cookie-domain`, `session-cookie-samesite`, `session-cookie-conditional-samesite-none`, `session-cookie-secure`, `session-cookie-max-age`, `session-cookie-expires`, `session-cookie-change-on-failure`

→ **Move to the server group**: ALB's session persistence lives in the server-group configuration, not in an Ingress annotation.

### 4.3 Authentication and authorization
`auth-type`, `auth-secret`, `auth-secret-type`, `auth-realm`, `auth-url`, `auth-keepalive`, `auth-keepalive-share-vars`, `auth-keepalive-requests`, `auth-keepalive-timeout`, `auth-method`, `auth-signin`, `auth-signin-redirect-param`, `auth-response-headers`, `auth-proxy-set-headers`, `auth-request-redirect`, `auth-snippet`, `auth-cache-key`, `auth-cache-duration`, `auth-always-set-cookie`, `auth-tls-secret`, `auth-tls-verify-depth`, `auth-tls-verify-client`, `auth-tls-error-page`, `auth-tls-pass-certificate-to-upstream`, `auth-tls-match-cn`

→ **Manual work**: the ALB Ingress annotation layer has no counterpart. Directions: implement auth in the application, use ALB AScript programmable scripting, or put WAF in front. The mTLS family (`auth-tls-*`) needs ALB's mutual-authentication capability evaluated.

Two more in the same domain:

| Annotation | Direction |
|------|---------|
| `satisfy` | Manual work: it decides whether several auth methods are "any of" or "all of". Since the auth itself has to be rebuilt in the application or AScript, express this combining semantics there too |
| `enable-global-auth` | **Safe to drop**: it controls whether the global auth in the ConfigMap is inherited, and ALB has no global-auth layer to inherit from |

### 4.4 Backend TLS
`proxy-ssl-secret`, `proxy-ssl-verify`, `proxy-ssl-verify-depth`, `proxy-ssl-ciphers`, `proxy-ssl-protocols`, `proxy-ssl-name`, `proxy-ssl-server-name`

→ **Move to the server group**: for an HTTPS backend use `backend-protocol: https` (**lower-case**), and configure the certificate verification policy on the server group / instance.

### 4.5 Request rewriting and redirects
| Annotation | Direction |
|------|---------|
| `upstream-vhost` | Manual work (rewriting the upstream Host) |
| `force-ssl-redirect` | ALB `actions.<svc>` (`type: Redirect`), or `ssl-redirect` |
| `permanent-redirect` | ALB `actions.<svc>` (`type: Redirect`) |
| `permanent-redirect-code` | The status code goes inside ALB `actions.<svc>` (`type: Redirect`) |
| `temporal-redirect` | ALB `actions.<svc>` (`type: Redirect`), 302 |
| `temporal-redirect-code` | The status code goes inside ALB `actions.<svc>` (`type: Redirect`) — the same destination as `permanent-redirect-code` |
| `from-to-www-redirect` | ALB `actions.<svc>` (`type: Redirect`) + `conditions.<svc>` (a Host condition to tell www from non-www) |
| `app-root` | ALB `actions.<svc>` (`type: Redirect`) |
| `proxy-cookie-domain` / `proxy-cookie-path` | Manual work: these rewrite the response `Set-Cookie`, and ALB's `InsertHeader` can only add a whole header, not rewrite an existing value |
| `proxy-redirect-from` / `proxy-redirect-to` | Manual work: these rewrite the `Location` response header returned by the backend — same reason as the row above, ALB has no "rewrite an existing response header" action |
| `preserve-trailing-slash` | Manual work: it preserves a trailing slash in the URI, and ALB's path-matching semantics already change during migration (see `generated-resources.md` §5.2). Do not tune this one in isolation; verify the whole hit set instead |

### 4.6 Backends and error pages
| Annotation | Direction |
|------|---------|
| `default-backend` (**the annotation**) | ALB `actions.<svc>` (`type: ForwardGroup` / `FixedResponse`). ⚠️ The annotation means "use this service **when the rule's Service has no active endpoints**", plus being the error-page source when `custom-http-errors` is also set (nginx's own annotations.md, "Default Backend"). **It is not `spec.defaultBackend`** — that one is the unmatched-path fallback, which the converter already handles by producing `from--<name>--default` |
| `custom-http-errors` | **All three**: `rule-direction.<svc>: Response` + `conditions.<svc>` (`ResponseStatusCode`) + `actions.<svc>` (`type: FixedResponse`). 🚨 No direction = every request to that path is replaced by the error page (the default direction is `Request`), and the webhook only skips the final-action check in the `Response` direction, so **the mistake is not caught**. See `migration-patterns.md` Level 1 |
| `custom-headers` | ALB `actions.<svc>` (`type: InsertHeader`) + **`rule-direction.<svc>: Response`**. ⚠️ Two preconditions: the value is a **ConfigMap reference** (`<namespace>/<configmap>`, which must be expanded header by header); and it uses `more_set_headers`, acting on **client response headers**, so omitting the direction turns it into upstream request headers — no effect, plus internal headers pushed to the backend |
| `server-alias` | ALB `conditions.<svc>` (Host condition), or an extra rule |
| `upstream-hash-by-subset` / `upstream-hash-by-subset-size` | Manual work: ALB's consistent hash is fixed to hashing a **query-string parameter** (see §3) and has no "subset hash" layer. If the source relies on it for sharded routing, rebuild that in the application or with several server groups |

### 4.7 Upstream retries
`proxy-next-upstream-tries`, `proxy-next-upstream-timeout`, `proxy-next-upstream`

→ **Do not drop them wholesale; look at the value first.** ALB Ingress has **no retry configuration at all** (no retry field at the annotation layer or in AlbConfig), so dropping these three is not "ALB has an equivalent" — it hands retry behaviour to the platform default with **no way to tune it**. Both directions bite:

| Source value | Consequence of dropping it |
|---|---|
| Exactly nginx's default (`proxy-next-upstream: error timeout`, `-tries: 0`, `-timeout: 0`) | Equivalent, **safe to drop** |
| Widened the retry surface (e.g. including `http_502` / `http_5xx` / `non_idempotent`) | After migration those status codes are no longer retried, and the error reaches the client during an incident |
| **Turned retries off (`off`)** | The most insidious: the customer set `off` precisely to avoid retries, and it cannot be turned off on ALB — **a non-idempotent endpoint (checkout, payment) may be submitted twice**. This one needs a human; never drop it silently |

### 4.8 Timeouts and buffering
**Timeouts**: `proxy-connect-timeout`, `proxy-send-timeout`, `proxy-read-timeout`
→ **Move to the listener / server group.**

**Buffering**: `proxy-request-buffering`, `proxy-buffering`, `proxy-buffer-size`, `proxy-buffers-number`, `proxy-busy-buffers-size`, `proxy-max-temp-file-size`, `client-body-buffer-size`, `proxy-http-version`
→ **Safe to drop**: these tune implementation details of nginx's own buffers, and ALB as a managed service does not expose the equivalent parameters, so dropping them does not change externally visible behaviour. ⚠️ The one to watch is `proxy-buffering: off` (which streaming/SSE relies on to disable buffering): ALB has no equivalent switch, so **the latency of streaming responses must be measured after migration**.

### 4.9 Rate limiting
| Annotation | Direction |
|------|---------|
| ~~`limit-rps`~~ | **An auto-converted item** (→ `traffic-limit-ip-qps`, see §1 item 19) — does not walk this tree. But it is **always reported 🟡** and the allowed throughput still has to be measured; see §2 row 1 |
| `limit-rpm` | ALB **`traffic-limit-ip-qps`** (also per IP; divide the value by 60). ⚠️ ALB's minimum is 1 QPS, so **anything below 60 rpm cannot be expressed** |
| `limit-connections` | ALB `traffic-limit-qps` (total rate limit; concurrent connections ≠ QPS, so the approximation needs confirming) |
| `limit-burst-multiplier` | Manual work (ALB rate limiting has no burst-multiplier concept) |
| `limit-rate` / `limit-rate-after` | Manual work (response-body throttling and its starting point have no counterpart at the ALB annotation layer) |
| `limit-whitelist` | Manual work (split with a SourceIp condition). ⚠️ A canary Ingress cannot carry `conditions.*`, see `migration-patterns.md` Level 1 |

### 4.10 Allow / deny lists
`whitelist-source-range`, `denylist-source-range`

→ ALB `conditions.<svc>` supports a **SourceIp** condition, which together with `actions.<svc>` (`type: FixedResponse`) implements this; ALB's ACL capability is also worth considering.

### 4.11 Traffic mirroring
| Annotation | Direction |
|------|---------|
| `mirror-target` | ALB `actions.<svc>` (`type: TrafficMirror`). ⚠️ **The target can only be a server group**: `TrafficMirrorConfig` = `TargetType` (single value `ForwardGroupMirror`) + `MirrorGroupConfig.ServerGroupTuples`, **not an arbitrary URL**. A source mirroring to an address outside the cluster cannot migrate |
| `mirror-request-body` | **Cannot be expressed** (confirmed): `TrafficMirrorConfig` has only the two fields above, with no switch for mirroring the request body. A source that set `off` to save bandwidth loses that control |
| `mirror-host` | **Cannot be expressed**: a mirrored request carries the original Host and ALB has no field to rewrite the mirror target's Host. ⚠️ If the mirror backend tells production from mirror by Host, it will **silently take the wrong branch** after migration |

### 4.12 Others
| Annotation | Direction |
|------|---------|
| `ssl-passthrough` | **Move this traffic to CLB / NLB (layer 4).** ⚠️ Not "change the listener to TCP/SSL on ALB" — ALB's listener protocols are only `HTTP` / `HTTPS` / `QUIC`. Once moved it no longer goes through the three resources, and its entry point and DNS need separate planning |
| `service-upstream` | **Safe to drop** (ALB's direct-to-backend behaviour already covers it) |
| `ssl-prefer-server-ciphers` | **Move to the listener**: the cipher-suite priority for client-side TLS is decided by the listener's **TLS security policy**, not the Ingress annotation layer. Same thing as `ssl-ciphers` (also 🔴) — choose the policy on the listener for both together |
| `connection-proxy-header` | **Safe to drop**: it changes the upstream `Connection` header, and connection reuse between ALB and the backend is managed by the platform, which does not expose the parameter |
| `http2-push-preload` | **Safe to drop**: HTTP/2 Server Push, deprecated in mainstream browsers and not offered by ALB |

### 4.13 Custom nginx directives
`configuration-snippet`, `server-snippet`, `stream-snippet`

→ **Manual work**: ALB cannot execute nginx directives. Break the snippet down directive by directive and map each to an ALB-native annotation (insert-header and the like), **AScript** programmable scripting, or the application. **This is the most common blocker in a migration — go through it directive by directive rather than ignoring it wholesale.**

### 4.14 WAF
| Annotation | Direction |
|------|---------|
| `enable-modsecurity` | **Move to the instance**: set the AlbConfig `edition` to `StandardWithWaf` (the WAF-enhanced edition), then configure the protection policy in the WAF console. ⚠️ This is **instance-scoped** while nginx's ModSecurity is per Ingress — every other Ingress on that ALB gets protected too |
| `enable-owasp-core-rules` | Same: the OWASP core rule set is enabled on the WAF side, not at the Ingress annotation layer |
| `modsecurity-snippet` | Manual work: custom ModSecurity rules must be rebuilt in the WAF console; the nginx syntax cannot be carried over |
| `modsecurity-transaction-id` | **Safe to drop**: it passes nginx's request ID to ModSecurity to correlate logs, and WAF has its own request identifier, so there is nowhere to plug this in |

### 4.15 Observability
| Annotation | Direction |
|------|---------|
| `enable-access-log` | **Move to the instance**: AlbConfig `spec.config.accessLogConfig` (`logProject` / `logStore`). ⚠️ Two differences: ① it is an **instance-scoped** switch while nginx's is per Ingress, so "logs for one Ingress only" is not possible; ② the webhook requires the **logStore name to start with `alb_`** or it rejects the config |
| `enable-rewrite-log` | **Safe to drop**: nginx's rewrite debug log; ALB has no counterpart and no need for one |
| `enable-opentelemetry` / `opentelemetry-trust-incoming-span` | Manual work: the ALB Ingress annotation layer has no tracing switch; carry it with ARMS or application-side instrumentation |

---

## 5. Count check

| Category | Count |
|------|------|
| 🟢 auto-converted (`nginx.ingress.kubernetes.io/*`) | 20 |
| 🟢 additional handling (`kubernetes.io/ingress.class`) | 1 |
| 🔴 unsupported | catch-all: everything else |
| 🟡 behaviour change | conditionally triggered (no fixed count) |

> An annotation in none of these categories: report it 🔴 with a reason (**never** ignore it silently), then walk the `migration-patterns.md` decision tree.
>
> Measured (cluster plus unit tests): **all 130 annotations** in the official ingress-nginx documentation are accounted for — either converted or reported, with **zero silent drops**.

---

## 6. Two mechanisms where an annotation takes effect without being on this Ingress

### 6.1 use-regex / rewrite-target taints the whole host

nginx's rule: if **any one** Ingress on a host uses `use-regex` or `rewrite-target`, then **every** path of **every** Ingress on that host is matched as a case-insensitive regex — regardless of their own pathType.

So during conversion:

- Every Ingress on that host (including one with no annotations at all) gets `alb.ingress.kubernetes.io/use-regex: "true"`, and its pathType is rewritten to `Prefix` (ALB can only express a regex through Prefix + use-regex) — including a source `Exact`, because nginx is no longer treating it as an exact match either.
- ⚠️ **ALB's regex is case-sensitive and nginx's `~*` is not.** Measured: with regex in effect, nginx answered `/images/x` from a `/Images` rule while ALB returned 503. Every path on that host is affected.
- ⚠️ **Anchoring — unverified, must be measured.** An nginx `~*` location matches the pattern **anywhere** in the URI; whether ALB anchors it to the whole path has not been tested. If it does, a request that only contains the pattern mid-string (`/prefix/api/v1/users` against `/api/v[0-9]+/.*`) stops matching after migration. Report it as a thing to verify, never as a known behaviour, and do not substitute an offline `re.fullmatch` check for a real request.
- A source Ingress holding both a tainted host and an untainted one is split into two Ingresses (the second named `--regex`), because ALB's use-regex is an **Ingress-wide** switch while nginx's is per host.

> When `rewrite-target`'s value equals the path it sits on, nginx considers nothing rewritten and does not enable regex — so it does not taint in that case.

> **The tainted Ingress also gets a 🟡**, but it has neither `use-regex` nor `rewrite-target` in its own YAML to point at, so that note's key is the annotation **on the output**, `alb.ingress.kubernetes.io/use-regex`, not any nginx annotation. Say plainly in the report that "this Ingress's matching was changed by another Ingress on the same host" — do not word it as if it had configured something itself.

### 6.2 ssl-redirect applies when "this Ingress has a tls block", not when "this host has a certificate"

**Cluster measurement** (2026-09-17, ACK test cluster, four probe Ingresses, a domain no wildcard certificate covers, a **valid** self-signed keypair, and a backend returning a recognisable 200):

| Source shape | Request | Result |
|---|---|---|
| The host is in `tls.hosts` with an exact certificate | `GET covered.../c` | **308** → https |
| Another host of **the same Ingress**, not in `tls.hosts`, with no certificate at all | `GET plain.../p` | **308** ← the deciding row |
| `tls.hosts` names a host that has **no rule** (coverage count 0) | `GET uncov.../u` | **308** |
| The Ingress has **no `tls:` block at all** | `GET nossl.../n` | **200**, no redirect |

Upstream documentation agrees: "By default the controller redirects (308) to HTTPS **if TLS is enabled for that ingress**".

**So the rule is: as long as the Ingress has a `spec.tls` block, `ssl-redirect` applies to all of its hosts; with no `tls:` block at all it applies to none. Which hosts the certificate covers has nothing to do with whether it redirects.**

> **But the implicit default is false** (measured in the same run): with **no `ssl-redirect` annotation written**, all three shapes (tls covers the host / tls covers nothing / no tls at all) returned **200**. The cause is `ssl-redirect = false` in `kube-system/nginx-configuration` — that is the **factory configuration** of ACK's `aliyun-ingress-controller`, not something this cluster changed. The upstream default is true, but reading only the source Ingress cannot tell which it is, so **do not add this annotation on the user's behalf**: adding it turns working plaintext traffic into a 308. The tool behaves this way (it only converts what the source wrote).

> Probe notes: the secret must hold a **valid** keypair (with an invalid key nginx falls back to the default certificate, and that host then "has a certificate", defeating the test), and the backend must return 200 for the probe path (`default/echo` 404s every path, which is indistinguishable from the stock default backend).

**The tool implements this** (`feature_redirect.go` only looks at `len(ing.Spec.TLS)`), so no compensation is needed during analysis:

| Source shape | nginx | Tool | Agree? |
|---|---|---|---|
| Has `tls:`, covers every host | redirects all | 🟢 annotation kept | ✅ |
| Has `tls:`, covers only some hosts | redirects all | 🟢 annotation kept | ✅ |
| Has `tls:`, covers no rule host at all | redirects all | 🟢 annotation kept | ✅ |
| No `tls:` at all | no redirect | annotation dropped, reported 🟢 | ✅ |

> History: the tool used to count "hosts covered by the certificate" via `hostsByTLSCoverage`, so the third row **dropped the annotation** (the output stopped redirecting) and the second row **raised a false 🟡**. Both were fixed along with this section's conclusion, which is why the behaviour-change trigger count fell from 7 to 6. `servesTLS` (which decides the 443 listener) used the same coverage check and moved with it — otherwise the third row would have become "the redirect was restored, pointing at a listener that was never created".
>
> The other half of the old conclusion still holds: **copying this annotation across when there is no `tls:` block is wrong** — ALB's switch is Ingress-scoped and ignores certificates, no 443 listener is generated, and normal HTTP traffic would turn into a 308 aimed at an HTTPS endpoint that does not exist.
