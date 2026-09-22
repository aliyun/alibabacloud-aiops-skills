# Weighted DNS cutover plan

The goal is a migration **no client notices**: one domain resolves to both the Nginx Ingress (CLB) and the ALB Ingress at the same time, traffic moves to ALB by weight, and Nginx is retired only after the new path is verified.

> This matches the official guide "Migrate workloads from a self-managed Nginx Ingress to an ALB Ingress". A weighted DNS cutover is not the only way; treat it as a reference.

---

## The constraint that shapes every step

**DNS does not allow an A record and a CNAME record to coexist on the same name.**

- CLB (what the Nginx Ingress uses) exposes an **IP** → A record
- ALB exposes a **default domain name** → CNAME record

So the CLB **must be given a temporary domain first**, turning both sides into CNAMEs, before they can coexist under one name with weights.

---

## Step 1: give the CLB a temporary domain

Taking the business domain `www.example.net` (currently an A record → CLB IP):

1. Open the **DNS console** → find `www.example.net` → resolution settings.
2. Find the **A record** pointing at the CLB IP, click Edit, and change the **host record** from `www` to `web0`, leaving everything else alone.
   → Result: `web0.example.net` A record → CLB IP
3. Add a new record:
   | Field | Value |
   |------|-----|
   | Type | `CNAME` |
   | Host record | `www` |
   | Value | `web0.example.net` (the temporary domain) |
   | TTL | default |

The chain is now `www.example.net` --CNAME--> `web0.example.net` --A--> CLB IP, and traffic is unaffected.

---

## Step 2: add the ALB CNAME and shift weight gradually

1. Get the ALB instance's domain:
   ```bash
   kubectl get albconfig
   ```
   The `DNSNAME` column looks like `alb-xxxxxxxx.<region>.alb.aliyuncs.com`.

2. Add a second **CNAME** record for `www`, with the ALB domain as its value.
   → `www` now has two CNAMEs: one to the temporary domain (CLB), one to the ALB.

3. Set the weights: resolution settings → find the CNAME record → the dropdown next to Edit → **Edit record set**, then set each weight.

   | Stage | CLB weight | ALB weight |
   |------|---------|---------|
   | Initial | 100 | **0** |
   | Canary 1 | 90 | 10 |
   | Canary 2 | 70 | 30 |
   | Canary 3 | 50 | 50 |
   | Canary 4 | 20 | 80 |
   | Done | **0** | 100 |

4. At each stage, run `dig` repeatedly and check how the answers are distributed:
   ```bash
   dig www.example.net
   ```
   - When it lands on CLB: `www... CNAME web0...` → `web0... A <CLB IP>`
   - When it lands on ALB: `www... CNAME alb-xxx....alb.aliyuncs.com` → several A records

---

## ⚠️ Mandatory before shifting any traffic

| Check | Why |
|--------|------|
| **Compare both sides' forwarding rules line by line** | The host / path / backend Service must match between Nginx and ALB |
| **Functional test** | Exercise the critical paths straight against the ALB domain (including canary, rewrite, CORS, HTTPS) |
| **🔴 unsupported annotations are resolved** | Every 🔴 item in the migration report has a landed plan, otherwise functionality is lost silently |
| **Placeholders replaced** | vSwitch IDs and certificate IDs must not still be `<...>` |
| **Quiet period** | Shift traffic during a trough |
| **Start from weight 0** | Attach it first without traffic, confirm resolution works, then raise the weight step by step |

> If the DNS provider **does not support CNAME weights**: fall back to "verify on a low-traffic domain first, then switch wholesale", or split traffic in the client / upstream. See the corresponding section of the official guide.

---

## Step 3: retire the Nginx Ingress

**Preconditions**: ALB weight is already 100, no new traffic is reaching Nginx, long-lived connections have drained, and the state has been observed quietly for a while.

1. **Delete the Nginx-related DNS records**: remove the `www` CNAME pointing at the temporary domain, and the `web0` A record.
2. **Hand over certificate renewal first** — before deleting the source Ingress, not after. The migration output deliberately **omits** `cert-manager.io/*` annotations (see `generated-resources.md` §4.1) while still referencing the same `spec.tls.secretName`. HTTPS works while the source Ingress exists; the moment it is deleted nothing renews that Secret, and **HTTPS breaks when the certificate expires**. Either point cert-manager at the Secret directly (a standalone Certificate resource), or add the annotations to the generated Ingress once you have confirmed no second Ingress is competing for it.
3. **Delete the Nginx Ingress resources**: Container Service console → the cluster → Network → Ingresses → Delete on the right of each Nginx Ingress.

   When deleting in bulk from the command line, **select by class, not by label**:

   ```bash
   # Correct — select by class. Ingress has no field selector for spec.ingressClassName,
   # so jsonpath is the only option.
   kubectl get ing -A -o jsonpath='{range .items[?(@.spec.ingressClassName=="nginx")]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}'
   # A source may carry only the legacy annotation and no spec field, so run this one too.
   kubectl get ing -A -o jsonpath='{range .items[?(@.metadata.annotations.kubernetes\.io/ingress\.class=="nginx")]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}'

   # Wrong — selecting by label is risky: the output inherits nearly every label of the source.
   kubectl delete ing -l <some label that marks nginx>
   ```

   The tool strips only the single `ingress-controller` label, so `-l ingress-controller=nginx` will **not** hit the generated objects today. But if the cluster marks nginx with a different key (say `lb-type: nginx`), that key *is* inherited, and deleting by it would take the freshly created ALB Ingresses with it. **The safest option is an explicit ns/name list recorded during the migration.**
4. **Uninstall the Nginx Ingress Controller component**: Add-ons → Networking → Nginx Ingress Controller → Uninstall.
   > The **CLB the component used is released automatically** when it is uninstalled, and stops being billed.
   > On an ACS (Container Compute Service) cluster: Applications → Helm → uninstall the corresponding release.

---

## Rollback

If anything goes wrong mid-cutover:

1. **Immediately** set the ALB weight back to `0` and the CLB weight back to `100`. DNS propagation is bound by TTL, which is why a shorter TTL is recommended during the cutover.
2. Keep the ALB-side resources for diagnosis — the `from--` prefix makes them easy to identify.
3. After fixing the cause, start again from a small weight.

> Because the migration output is uniformly prefixed `from--` and **coexists** with the original Nginx resources, rolling back requires rebuilding nothing on the Nginx side. That is this plan's safety margin.
