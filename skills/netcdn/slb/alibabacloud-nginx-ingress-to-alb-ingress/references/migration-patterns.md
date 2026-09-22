# Decision tree for unsupported annotations

For every 🔴 unsupported annotation, walk the four levels below **in order** and stop at the first hit.

```
1. Is there an ALB-native annotation?        → rewrite with it
2. Safe to drop?                             → remove it (ALB's default already covers it)
3. Instance / listener / server-group config? → move it off the Ingress, onto AlbConfig or the server group
4. None of the above?                         → manual work (application change / AScript / WAF)
```

---

## Level 1: an ALB-native annotation can replace it

### First, get the `actions.*` / `conditions.*` annotation name right

The suffix of these two annotation families **must be the Service name referenced by that path in `spec.rules`** — not the type of the action or condition:

```go
// model_build_listener_rules.go
ing.Annotations[fmt.Sprintf("alb.ingress.kubernetes.io/actions.%s", path.Backend.Service.Name)]
ing.Annotations[fmt.Sprintf("alb.ingress.kubernetes.io/conditions.%s", path.Backend.Service.Name)]
```

So it is written like this:

```yaml
metadata:
  annotations:
    # suffix response-503 = the service name referenced in rules below
    # (it may be a placeholder name that does not exist)
    alb.ingress.kubernetes.io/actions.response-503: |
      [{"type":"FixedResponse","FixedResponseConfig":{...}}]
spec:
  rules:
    - http:
        paths:
          - path: /old
            pathType: Prefix
            backend:
              service:
                name: response-503        # ← must match the annotation suffix
                port: { number: 80 }
```

⚠️ **Write the suffix as an action type (say `actions.redirect`) with no service of that name in rules, and the annotation is never read — the configuration silently does nothing, with no error anywhere.** The action type belongs in the JSON `type` field.

**Action types ALB supports** (verified in `pkg/util/constant.go`, nine of them):

| type | Purpose |
|---|---|
| `ForwardGroup` | Forward to a server group. **Note the value is `ForwardGroup`, not `Forward`** |
| `Redirect` | Redirect (the status code goes in the config) |
| `FixedResponse` | Return a fixed response |
| `InsertHeader` / `RemoveHeader` | Add / remove a header |
| `Rewrite` | Rewrite the path (the action behind the `rewrite-target` annotation) |
| `TrafficLimit` | Rate limit (the action behind the `traffic-limit-*` annotations) |
| `TrafficMirror` | Traffic mirroring |
| `Cors` | CORS (the action behind `enable-cors` and friends) |

**Condition fields ALB supports** (verified in source): seven usable in the request direction — `Host`, `Path`, `Header`, `QueryString`, `Method`, `Cookie`, `SourceIp`. The response direction has its own two, `ResponseStatusCode` and `ResponseHeader` (defined separately in `constant.go`), and they only mean anything on a rule carrying `rule-direction.<svc>: Response` — which is exactly how `custom-http-errors` migrates.

> 🚫 **`Model` is defined but not usable from an Ingress annotation.** `RuleConditionFieldModel = "Model"` exists in `pkg/util/constant.go`, but the annotation-facing `Condition` struct has **no `ModelConfig` field** and the recognised-type list (`model_build_listener_rules.go`, the `lowerRuleConditionField*` set) omits it; `ModelConfig` appears only in the vendored SDK's *ListRules response* type, i.e. the API can report one, the controller cannot build one. Writing `{"Type":"Model"}` gives the value nowhere to live, so treat `Model` as unavailable and do not offer it as a migration target.

> **Which capabilities have a dedicated annotation and which need hand-written JSON** (verified against the full ALB annotation set; do not assume "most of them have a dedicated annotation"):
>
> | | Dedicated annotation exists | Only `actions.*` / `conditions.*` JSON |
> |---|---|---|
> | action | `Rewrite` (`rewrite-target`), `TrafficLimit` (`traffic-limit-qps` / `-ip-qps`), `Cors` (`enable-cors` etc.), `Redirect` (only the HTTP→HTTPS case, via `ssl-redirect`) | `FixedResponse`, `ForwardGroup`, `InsertHeader`, `RemoveHeader`, `TrafficMirror`, and any `Redirect` that is not the HTTPS one |
> | condition | `Host` / `Path` are expressed by `spec.rules` (not by an annotation); `Header` / `Cookie` have `canary-by-header` / `canary-by-cookie` **only in the canary case** | `QueryString`, `Method`, `SourceIp`, `ResponseStatusCode`, `ResponseHeader`, and `Header` / `Cookie` outside the canary case (`Model` is neither — see the note above) |
>
> Prefer a dedicated annotation over hand-written JSON — but the capabilities in the right column have **only** the JSON route, so do not go looking for a dedicated annotation that does not exist.
>
> 🚨 **A canary Ingress may not carry any `conditions.<svc>` annotation.** The controller has a dedicated check for an Ingress with `canary: "true"`; finding a custom condition it reports `can't exist Canary and customize condition at the same time` and `return err`s out of building the rules for the whole listener — **every Ingress on that listener stops having its rules published, not just this one**. So an Ingress in the middle of a canary rollout cannot add an allow-list or header-based split through `conditions.*`; it needs a different approach (see the replacement table below).

### Replacement table

| nginx annotation | ALB replacement | Conversion / caveat |
|-----------|---------|----------|
| ~~`limit-rps`~~ | — | **This is an auto-converted item**, not 🔴, and does not walk this tree (see annotation-mapping.md §1). But it is **always reported 🟡** and the allowed throughput must be measured |
| `limit-rpm` | `traffic-limit-ip-qps` | Also per-IP; divide the value by 60. ⚠️ ALB's minimum is 1 QPS, so **anything below 60 rpm cannot be expressed** |
| `limit-connections` | `traffic-limit-qps` | Concurrent connections ≠ QPS; the semantics are only close, so load-test to confirm |
| `mirror-target` | `actions.<svc>` + `type: TrafficMirror` | ⚠️ **The target can only be a server group, not an arbitrary URL**: `TrafficMirrorConfig` has only `TargetType` + `MirrorGroupConfig.ServerGroupTuples`, and `TargetType`'s single value is `ForwardGroupMirror`. A source mirroring to an address outside the cluster cannot migrate |
| `custom-headers` | `actions.<svc>` + `type: InsertHeader`, **and** `rule-direction.<svc>: Response` | ⚠️ Two preconditions to confirm first, or the configuration does nothing: ① **the value is a ConfigMap reference** (`<namespace>/<configmap>`), not inline headers, so the keys and values must be pulled out of the ConfigMap and expanded one by one; ② it uses nginx's `more_set_headers` and acts on the **response headers returned to the client** — with no direction ALB defaults to `Request` (upstream request headers), so the client never receives them and internal headers are pushed to the backend instead |
| `force-ssl-redirect` | `ssl-redirect` (the dedicated annotation, preferred) or `actions.<svc>` + `type: Redirect` | |
| `permanent-redirect` / `permanent-redirect-code` | `actions.<svc>` + `type: Redirect` | 301; the status code goes in the config |
| `temporal-redirect` | `actions.<svc>` + `type: Redirect` | 302 |
| `app-root` | `actions.<svc>` + `type: Redirect` | Root-path redirect |
| `default-backend` (**the annotation**, not `spec.defaultBackend`) | `actions.<svc>` + `type: ForwardGroup` or `FixedResponse` | ⚠️ Do not conflate it with `spec.defaultBackend`. The annotation means "use this service **when the rule's Service has no active endpoints**", plus "the source of the error page when `custom-http-errors` is also set". ALB has no "swap server groups when the backend is entirely down" switch, so it can only be approximated with health checks plus server-group orchestration, or handled in the application. `spec.defaultBackend` (the unmatched-path fallback) is a different thing that the converter already handles — see SKILL.md Step 1 |
| `custom-http-errors` | **All three, none optional**: `rule-direction.<svc>: Response` + `conditions.<svc>` (`ResponseStatusCode`) + `actions.<svc>` (`type: FixedResponse`) | 🚨 **Omitting the direction takes the whole path down.** nginx triggers on the **status code the upstream returned**; an ALB rule with no direction defaults to `Request` (`buildRuleDirection` returns `RuleRequestDirection` when the annotation is absent), so **every request** to that path is replaced by the error page and the backend receives no traffic at all. And the webhook's "at least one final-type action" check **is only skipped when the direction is `Response`** (`ingress_validator.go`), so the Request-direction mistake is not caught — the wrong form publishes cleanly. A complex error page still belongs in the application |
| `whitelist-source-range` | `conditions.<svc>` (`SourceIp`) + `actions.<svc>` (`type: FixedResponse`) as the fallback | ⚠️ Each of the three routes has its own constraint; do not stop at the first: ① **`conditions` with SourceIp** — Ingress-scoped, matching nginx's granularity, and the first choice; ② **a listener ACL (`aclConfig`)** — this is **listener-scoped** while nginx's allow-list is per Ingress, so when several Ingresses share one ALB a single ACL becomes a global allow-list for every domain on that listener; ③ **an instance security group (`securityGroupIds`)** — **cannot coexist** with an ACL; configuring both reports `acl and securityGroupIds cannot use together` during reconciliation (note: a reconciliation failure, not an admission rejection — the object applies fine and the message only shows up in the Ingress events) |
| `denylist-source-range` | `conditions.<svc>` (`SourceIp`) + `FixedResponse` | |
| `server-alias` | `conditions.<svc>` (`Host`), or just add the host to `spec.rules` | The latter is simpler |
| `more_clear_headers` inside a snippet | `actions.<svc>` + `type: RemoveHeader` | Easy to miss this replacement when breaking a snippet apart |

> ⚠️ The value of `actions.*` / `conditions.*` is JSON. **The full schema is in §1b below — use it. Never go to the web for it and never invent field names**: this skill works offline, exactly like the conversion tool.

---

## 1b. The `actions.*` / `conditions.*` JSON schema (complete, offline)

Transcribed from the controller's annotation-facing structs — `pkg/model/alb/configcache/config_types.go` for the shapes and `pkg/util/constant.go` for the type strings. This is the struct the annotation is **unmarshalled into**, not the internal model, so the casing below is the casing that binds.

Both annotations take a **JSON array**. Each element carries `"Type"` plus exactly one `<Type>Config` sibling:

```yaml
alb.ingress.kubernetes.io/actions.<svc>: |
  [{"Type":"FixedResponse","FixedResponseConfig":{"ContentType":"text/plain","Content":"...","HttpCode":"503"}}]
alb.ingress.kubernetes.io/conditions.<svc>: |
  [{"Type":"ResponseStatusCode","ResponseStatusCodeConfig":{"Values":["404","500"]}}]
```

### Actions — nine types

| `"Type"` | Config key | Fields |
|---|---|---|
| `ForwardGroup` | **`forwardConfig`** (lower-case `f`) | `serverGroups: [{serverGroupID, serviceName, servicePort, weight}]` (**all lower-case initial**), optional `ServerGroupStickySession: {Enabled, Timeout}` |
| `FixedResponse` | `FixedResponseConfig` | `ContentType`, `Content`, `HttpCode` |
| `Redirect` | `RedirectConfig` | `Host`, `Path`, `Query`, `Port`, `Protocol`, `HttpCode` |
| `Rewrite` | `RewriteConfig` | `Host`, `Path`, `Query` |
| `InsertHeader` | `InsertHeaderConfig` | `Key`, `Value`, `ValueType`, `CoverEnabled` |
| `RemoveHeader` | `RemoveHeaderConfig` | `Key` |
| `TrafficLimit` | `TrafficLimitConfig` | `QPS`, **`QPSPerIp`** — both **strings** here |
| `TrafficMirror` | `TrafficMirrorConfig` | `TargetType` (only `ForwardGroupMirror`), `MirrorGroupConfig: {ServerGroupTuples: [{serverGroupID, serviceName, servicePort, weight}]}` |
| `Cors` | `CorsConfig` | `AllowOrigin[]`, `AllowMethods[]`, `AllowHeaders[]`, `ExposeHeaders[]`, `AllowCredentials`, **`MaxAge` (string)** |

### Conditions — seven request + two response

| `"Type"` | Config key | Fields |
|---|---|---|
| `Host` / `Path` / `Method` / `SourceIp` | `HostConfig` / `PathConfig` / `MethodConfig` / `SourceIpConfig` | `Values: [string]` |
| `Header` | `HeaderConfig` | `Key`, `Values: [string]` |
| `Cookie` / `QueryString` | `CookieConfig` / `QueryStringConfig` | `Values: [{Key, Value}]` |
| `ResponseStatusCode` | `ResponseStatusCodeConfig` | `Values: [string]` — **needs `rule-direction.<svc>: Response`** |
| `ResponseHeader` | `ResponseHeaderConfig` | `Key`, `Values: [string]` — **needs `rule-direction.<svc>: Response`** |

### Four traps you cannot infer from the field names

1. **`ContentType` is mandatory on `FixedResponse`.** `buildFixedResponseAction` opens with `if len(ContentType) == 0 { return errors.New("missing FixedResponseConfig") }` — omit it and the rule build fails, taking the listener's rules with it. `Content` and `HttpCode` are not checked.
2. **`ForwardGroup` breaks the casing pattern.** Its config key is `forwardConfig`, not `ForwardGroupConfig` / `ForwardConfig`, and every field inside `serverGroups` starts lower-case. Every other action's config key is `<Type>Config` in upper camel.
3. **Numbers that look like numbers are strings.** `TrafficLimitConfig.QPS` / `QPSPerIp` and `CorsConfig.MaxAge` are `string` in the annotation form even though the internal model types them `int`/`int64`. Write `"QPS":"100"`, not `"QPS":100`.
4. **`QPSPerIp`, not `PerIpQps`.** The internal model calls the field `PerIpQps`; the annotation binds `QPSPerIp`. The wrong spelling parses without error and silently rate-limits nothing. (Prefer the dedicated `traffic-limit-qps` / `traffic-limit-ip-qps` annotations and avoid this entirely.)

> Go's `json.Unmarshal` matches field names case-insensitively, so `"type"` also binds where the table says `"Type"`. Do not rely on it — write the casing above, so a future strict-decoding change does not break the output.

---

## Level 2: safe to drop

Just remove it: ALB's default behaviour already covers it and the externally visible semantics do not change.

| Annotation | Why dropping is safe |
|------|---------|
| `service-upstream` | ALB connects straight to the backend Pod/ECS, so the switch is unnecessary |
| `proxy-request-buffering`, `proxy-buffering`, `proxy-buffer-size`, `proxy-buffers-number`, `proxy-busy-buffers-size`, `proxy-max-temp-file-size`, `client-body-buffer-size`, `proxy-http-version` | These tune implementation details of nginx's own buffers; ALB is managed and does not expose them, so dropping them changes no externally visible behaviour. ⚠️ Exception: `proxy-buffering: off` (which streaming/SSE relies on to disable buffering) has no ALB equivalent — **the latency of streaming responses must be measured** |
| `connection-proxy-header` | Changes the upstream `Connection` header; connection reuse between ALB and the backend is managed by the platform |
| `http2-push-preload` | HTTP/2 Server Push, deprecated in mainstream browsers and not offered by ALB |
| `enable-rewrite-log` | nginx's rewrite debug log; ALB has no counterpart and no need for one |
| `enable-global-auth` | It controls whether the global auth in the ConfigMap is inherited, and ALB has no such layer |
| `modsecurity-transaction-id` | Passes a request ID to ModSecurity to correlate logs; WAF has its own request identifier and there is nowhere to plug this in |

> 🚨 **The three `proxy-next-upstream*` annotations do not belong at this level — do not drop them on the theory that "ALB has equivalent retry behaviour".** The fact is **ALB Ingress has no retry configuration at all** (no retry field at the annotation layer or in AlbConfig), so dropping them hands retries to the platform default with no way to tune them. It is only equivalent, and only safe, when the value is exactly nginx's default (`error timeout` / `-tries: 0` / `-timeout: 0`). A value of `off` is **the most dangerous** — a customer sets `off` precisely to prevent retries, and a non-idempotent endpoint could be submitted twice. Case-by-case judgement in `annotation-mapping.md` §4.7.

---

## Level 3: move it to the instance / listener / server group

ALB **has** these capabilities, but they are **not expressed through Ingress annotations** — they are set on the AlbConfig (instance / listener) or in the server-group configuration. Remove them from the Ingress during conversion and list them in the migration report as "must be configured on the ALB side".

| Capability | nginx annotation | Where it lives on ALB |
|------|-----------|-----------|
| Session persistence | `affinity`, `affinity-mode`, `affinity-canary-behavior`, `session-cookie-*` (9 annotations) | **Server-group** session persistence settings |
| Backend TLS verification | `proxy-ssl-*` (7 annotations) | The backend protocol goes in `backend-protocol: https` (**lower-case**); the verification policy lives on the server group / instance |
| Timeouts | `proxy-connect-timeout`, `proxy-send-timeout`, `proxy-read-timeout` | **Listener** and **server-group** timeout settings |
| Client-side TLS | `ssl-ciphers`, `ssl-prefer-server-ciphers` | The **listener's** TLS security policy (cipher suites and their order), not the Ingress annotation layer |
| WAF | `enable-modsecurity`, `enable-owasp-core-rules` | AlbConfig `edition: StandardWithWaf` plus a WAF console policy. ⚠️ **Instance-scoped** — every other Ingress on that ALB gets protected too |
| Access logs | `enable-access-log` | AlbConfig `spec.config.accessLogConfig` (`logProject` / `logStore`). ⚠️ Two things: ① **instance-scoped**, so it cannot be enabled for one Ingress only; ② the webhook requires the **logStore name to start with `alb_`** or it rejects the config |
| SSL passthrough | `ssl-passthrough` | ⚠️ **Not a matter of changing the listener protocol on ALB** — ALB's listener protocols are only `HTTP` / `HTTPS` / `QUIC`, with no TCP/SSL. This traffic has to **move to CLB or NLB** (layer 4), at which point it no longer goes through AlbConfig + IngressClass + Ingress and needs its entry point and DNS planned separately |

> ⚠️ What this level has in common is a **granularity mismatch**: the nginx annotation is per Ingress while the ALB side is mostly instance-, listener- or server-group-scoped. Session persistence and backend TLS land on the server group (close enough), but WAF, access logs and the TLS security policy land on the instance or the listener — so when several source Ingresses share one AlbConfig, "enable it for one" means "enable it for every domain on that listener". Say so in the migration report.

---

## Level 4: manual work required

The ALB Ingress annotation layer has **no** counterpart, so something has to change. Three directions:
1. **Implement it in the application** (most common, most controllable)
2. **ALB AScript** programmable scripting (custom logic executed on ALB)
3. **Put WAF in front** (for security features)

| Annotation | Suggested direction |
|------|---------|
| `auth-type` / `auth-secret` / `auth-secret-type` / `auth-realm` (Basic auth) | Application, or AScript |
| `auth-url` / `auth-signin` / `auth-method` / `auth-response-headers` / `auth-proxy-set-headers` / `auth-request-redirect` / `auth-snippet` / `auth-keepalive*` (external auth, 13 annotations) | Gateway auth in the application, or an external check issued from AScript |
| `auth-tls-*` (mTLS, 6 annotations) | Evaluate ALB's mutual-authentication capability; otherwise the application |
| `configuration-snippet` / `server-snippet` / `stream-snippet` | **Break it down directive by directive** and map each (see below) |
| `upstream-vhost` | Application, or rewrite the upstream Host from AScript |
| `limit-rate` | Application (response body throttling) |
| `limit-burst-multiplier` | ALB rate limiting has no burst concept; judge case by case |
| `limit-whitelist` | Split with a SourceIp condition and leave the exempt path unlimited |
| `canary-by-header-pattern` | ALB matches a header value exactly; a regex match needs manual work |
| ~~`canary-weight-total`~~ | **Auto-converted** — the tool folds it into `canary-weight` as a percentage, so no manual work is needed |
| `mirror-request-body` | **Cannot be expressed** (confirmed, not "to be confirmed"): ALB's `TrafficMirrorConfig` has only `TargetType` and `MirrorGroupConfig`, with no switch for mirroring the request body. A source that set `off` to save bandwidth loses that control after migration |
| `mirror-host` | **Cannot be expressed**: an ALB mirrored request carries the original Host and there is no field to rewrite the mirror target's Host. ⚠️ If the mirror backend distinguishes production from mirror by Host, it will silently take the wrong branch after migration — confirm before migrating that the mirror backend does not depend on Host |
| `custom-http-errors` (complex error pages) | Application |

### How to break down a snippet (a frequent blocker)

**Do not ignore a snippet wholesale.** List the nginx directives inside it and judge each one separately:

| Common directive in a snippet | Mapping |
|-------------------|------|
| `more_set_headers` / `add_header` | ALB `actions.<svc>` (`type: InsertHeader`) + **`rule-direction.<svc>: Response`** — these two directives change the **response headers returned to the client**, and without the direction they become upstream request headers (no effect, plus the headers are pushed to the backend) |
| `proxy_set_header <anything but Host>` | ALB `actions.<svc>` (`type: InsertHeader`) with the default `Request` direction, which is exactly what it changes |
| `more_clear_headers`, or `add_header` used to remove | ALB `actions.<svc>` (`type: RemoveHeader`), with the direction chosen the same way |
| `return` / `rewrite ... redirect` | ALB `actions.<svc>` (`type: Redirect`) |
| `limit_req` / `limit_conn` | ALB `traffic-limit-ip-qps` (per IP) / `traffic-limit-qps` (total) |
| `allow` / `deny` | ALB `conditions` (SourceIp) + `actions.<svc>` (`type: FixedResponse`). ⚠️ If that Ingress is a canary this route is closed — a canary cannot carry `conditions.*`, see Level 1 |
| `proxy_set_header Host` | Upstream Host rewriting → manual work |
| `set` / `if` / Lua logic | **AScript** or the application |

In the migration report, output a "directive → mapping → covered?" table for each snippet and mark the directives that are **not covered**, so the user knows exactly what the gap is.

---

## The four possible conclusions

In the migration report, every 🔴 annotation must be given one of these four conclusions. None may be left blank:

| Conclusion | Meaning |
|------|------|
| Replaced with an ALB annotation | Level 1 hit — give the replacement annotation and its value |
| Dropped | Level 2 hit — explain why that is safe |
| Must be configured on the ALB side | Level 3 hit — name the location (listener / server group) |
| Manual work required | Level 4 — give the direction (application / AScript / WAF) and describe the gap |
