# Verification method

Two layers: **static checks before deploying** (local / cluster dry-run) and **behavioural verification after deploying** (real traffic).

---

## 1. Before deploying: YAML format check (client-side dry-run)

```bash
kubectl apply -f ingress.yaml       --dry-run=client
kubectl apply -f ingressclass.yaml  --dry-run=client
kubectl apply -f albconfig.yaml     --dry-run=client
```

**It does exactly one thing: confirm the YAML parses into a legal object** (indentation, field names, types, required fields). Nothing is written to the cluster and no business validation happens.

### About the AlbConfig line

`--dry-run=client` does not contact the server for admission, but kubectl still has to resolve the `AlbConfig` type from cluster discovery. So in an environment **without the ALB Ingress Controller installed**, that line reports:

```
error: unable to recognize "albconfig.yaml": no matches for kind "AlbConfig" in version "alibabacloud.com/v1"
```

That is an **environment problem, not a YAML mistake**. Two ways forward: install the ALB Ingress Controller first (it is step one of deployment anyway), or validate only the Ingress and IngressClass for now and leave the AlbConfig until the controller is in place.

### Reading the result

| Output | Meaning | What to do |
|------|------|------|
| `xxx created (dry run)` | The YAML is well-formed | ✅ passed |
| `error validating data: ...` | A field name, type or required field is wrong | Fix the field named in the error |
| `no matches for kind "AlbConfig"` | The CRD is not installed | See above — an environment problem |

### ⚠️ What dry-run cannot do (tell the user)

**It only looks at format; passing does not mean apply will bring an ALB up.** A client-side dry-run does **not** check:

- whether the `vSwitchId` exists, is in the same VPC as the cluster, or covers two zones (the placeholder `<VSW_ID_ZONE_A>` passes too)
- whether the `CertificateId` is valid
- whether the backend Service / Pods exist
- whether a resource name collides with something already in the cluster (it never contacts the server, so it cannot tell)
- whether the references between resources are consistent (an Ingress referring to an IngressClass that does not exist yet passes fine)
- any ALB-side business rule — listener ports, annotation values, canary preconditions and the like are only reported by the controller during reconciliation

So after the format check, **the static self-check in the next section is not optional**: placeholders and the reference chain can only be caught by grep.

---

## 2. Before deploying: static self-check

```bash
# The reference chain between the three resources
grep -nE "ingressClassName|kind: AlbConfig|controller: ingress.k8s.alibabacloud/alb" *.yaml

# Any placeholder left behind (must print nothing)
grep -nE "<VSW_ID|<CERT_ID|<REGION|<ADDRESS_TYPE" *.yaml && echo "❌ placeholders still present — do not apply"

# [MOST IMPORTANT] read the warning events after apply — "accepted" is not "in effect".
#   Writing the object into the cluster only means the format was fine; whether it takes effect is
#   decided asynchronously by the controller afterwards, and the reason for failure is only written
#   into events: a missing listener, a duplicate listener, a Secret that is absent or malformed, a
#   backend Service that does not exist, a vSwitch still holding a placeholder so ALB creation fails,
#   a path the cloud judged illegal — all of them land here.
#   ⚠️ Verified (2026-09): a cloud rejection (FailedApplyModel) is recorded with the **same requestId**
#      on [every Ingress on that ALB] **and** on [the AlbConfig] — check both. An earlier version of
#      this document claimed it appears only on the Ingress and not on the AlbConfig; that was
#      refuted by reproduction.
#   ⚠️ Which gives a diagnostic rule: if your own Ingress shows FailedApplyModel but the path or
#      parameter in the message is **not yours**, someone else's illegal configuration on the same
#      ALB is holding up the whole group.
kubectl get events -n <ns> --field-selector involvedObject.kind=Ingress,involvedObject.name=<from--xxx>
kubectl get events -A --field-selector involvedObject.kind=AlbConfig,involvedObject.name=<albconfig-name>
kubectl describe ingress <from--xxx> -n <ns> | sed -n '/Events/,$p'
# In effect looks like: Normal/SuccessfullyReconciled plus an ALB domain in status
kubectl get ingress <from--xxx> -n <ns> -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Do listen-ports and the AlbConfig listeners agree?
grep -n "listen-ports" ingress.yaml
grep -n -A2 "listeners:" albconfig.yaml

# No nginx annotation should survive in the output (conversion never carries them over;
# any output here means the generation step missed one)
grep -n "nginx.ingress.kubernetes.io/" ingress.yaml && echo "❌ nginx annotation left in the output — remove it"
# cert-manager / external-dns are dropped the same way — but arrange certificate renewal
# before deleting the source Ingress
grep -nE "cert-manager\.io/|external-dns\." ingress.yaml
```

---

## 3. After deploying: resource readiness

```bash
# Was the ALB instance created, and did it get a domain?
kubectl get albconfig
# Expect the instance ID and ALB domain columns to be non-empty. The column names come from the CRD's
# printer columns and differ between versions — when in doubt read the fields directly
# (the field in status is all lower-case: dnsname):
kubectl get albconfig -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.loadBalancer.id}{"\t"}{.status.loadBalancer.dnsname}{"\t"}{.status.loadBalancer.phase}{"\n"}{end}'
# phase should be Active (other values: Configuring / Failed / Deleting)

# Has the ALB controller taken over the IngressClass?
kubectl get ingressclass

# Have the Ingresses been given an address?
kubectl get ingress -A
# Expect the ADDRESS column to show the ALB domain

# Any error in the controller log — a failed cloud apply does not always show up in status
kubectl -n kube-system logs deploy/alb-ingress-controller --tail=100 | grep -iE "error|fail"
```

> **Important**: a failed cloud call often **does not appear in the Ingress/AlbConfig status**. The controller log is the place to confirm.

---

## 4. After deploying: behavioural verification (before shifting traffic)

Exercise the critical paths straight against the ALB domain and compare each against the Nginx side:

```bash
ALB=$(kubectl get albconfig -o jsonpath='{.items[0].status.loadBalancer.dnsname}')

# Basic forwarding
curl -sv -H "Host: www.example.net" "http://$ALB/svc" -o /dev/null

# Path rewrite (confirm the path reaching the backend is what you expect)
curl -s -H "Host: www.example.net" "http://$ALB/svc/abc"

# HTTPS / certificate
curl -sv "https://www.example.net/" --resolve "www.example.net:443:$(dig +short $ALB | head -1)" -o /dev/null

# CORS
curl -s -I -H "Origin: https://foo.com" -H "Host: www.example.net" "http://$ALB/svc"

# Canary (by header / by weight)
curl -s -H "Host: www.example.net" -H "<canary-header>: <value>" "http://$ALB/svc"
```

### The checklist to go through item by item

| Check | Why |
|--------|--------|
| Does path matching agree with Nginx? | On a regex-mode host, pathType should be `Prefix` + `use-regex: "true"` with the path unchanged; only a non-regex `ImplementationSpecific` gets `*` appended. **Note ALB's regex is case-sensitive and nginx's is not** |
| Is the rewrite result correct? | The `$N` → `${N}` syntax change |
| Canary semantics | `canary-weight` combined with `canary-by-header`/`cookie` means something different on ALB |
| Scheduling algorithm | `load-balance: ewma` has no ALB counterpart and was replaced |
| The features behind 🔴 annotations | Authentication / session persistence / snippets — is each covered by its replacement? (**rate limiting is auto-converted**, see the next row) |
| How much traffic the rate limit actually lets through | `limit-rps` is auto-converted to `traffic-limit-ip-qps`, but the same number lets very different traffic through: nginx counts per replica and allows a 5x burst, ALB counts once with no burst, and this tool emits one rule per path, each counting independently. **Measure it**; do not assume equivalence. Numbers and method below in "How to test rate limiting" |
| Session persistence | ⚠️ **The tool does not convert** `affinity` / `session-cookie-*`; they are reported 🔴. ALB's session persistence lives at the server-group level (`sticky-session` and friends) and must be **configured by the user** and confirmed — do not assume the migration brought it over |

---

## 5. How to test rate limiting (there is a trap; miss it and you measure nothing)

> 🚨 **Load-testing straight from a cloud machine or container may not trigger per-IP rate limiting at all.** Verified: a container's egress goes through a SNAT pool, so 60 concurrent requests arrived with different source IPs (`106.11.32.66`, `106.11.32.90`, `106.11.32.74`, …) — and nginx's `limit-rps` and ALB's `traffic-limit-ip-qps` **both count per client IP**. All 60 requests were allowed through, which looks like "the rate limit is not working" but is really the wrong test.
>
> **The right way: send them down a single keep-alive connection.** One TCP connection pins one source IP, which triggers per-IP limiting reliably:
>
> ```python
> c = http.client.HTTPConnection(endpoint, 80, timeout=20)
> for i in range(60):
>     c.request("GET", "/", headers={"Host": host, "Connection": "keep-alive"})
>     r = c.getresponse(); r.read()
>     print(i + 1, r.status)          # note which request is the first to be limited
> ```
>
> Testing from a machine with a fixed public IP works too. **Do not** use concurrent connections unless you have confirmed the egress IP is fixed.

**Measured difference with the same setting on both sides** (`limit-rps: 5` vs `traffic-limit-ip-qps: 5`, 60 requests down one connection):

| | Allowed | Limited | First limited at |
|---|---|---|---|
| nginx | **37** | 23 | request 32 |
| ALB | **2** | 58 | request 2 |

Roughly an order of magnitude apart: nginx allows a 5x burst by default and **counts separately per controller replica**, while ALB counts once with no burst. Carrying the nginx number straight over to ALB **tightens the limit by an order of magnitude**, which can turn normal traffic into errors at peak.

> ⚠️ **Both sides answer `503` when limiting** (nginx's `limit-req-status-code` defaults to 503; ALB was measured returning 503 too). So a 503 after migration **cannot** be read as "the backend is down" — rate limiting, rules not yet published, and a backend with no healthy endpoints all share that code. Use the events above and the ALB monitoring to tell them apart.

---

## 6. Cutover verification

See `dns-cutover.md`: after every weight change, run `dig` repeatedly to confirm how answers are distributed, and watch both the application monitoring and the ALB monitoring (QPS, status codes, RT).
