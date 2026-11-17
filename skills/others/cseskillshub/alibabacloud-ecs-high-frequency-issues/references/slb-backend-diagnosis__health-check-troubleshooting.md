# Health-Check Failures, 502 and 404 (Scenario B)

Scope: the load balancer reports the backend as unhealthy ("the health-check
port on the backend server is not in a normal listening state"), or clients
get 502 / 404 through the load balancer while the backend "looks fine".

Division of labor (hard boundary of this tier):

- Cloud-readable facts (this skill queries them): backend instance status,
  zone, type, security-group bindings, latest CPU/traffic datapoints, EIP
  facts.
- NOT cloud-readable by this skill (no verified load-balancer API in this
  tier): listener port mapping, health-check configuration and results,
  server-group membership, access-control whitelists, LB edition limits.
  These come from customer console self-checks and customer-run commands
  whose output the customer returns.
- NEVER executed by this skill: any command inside a customer instance. The
  `ss` / `netstat` / `curl` commands below are guidance for the CUSTOMER to
  run and return verbatim.

> Source discipline: rules below are distilled from real support tickets of
> this tier; official SLB/ALB health-check documentation URLs are PENDING
> verification. Cite only the verified links at the bottom.

## Decision tree (mirrors the entry script `--symptom health-check` / `--symptom http-5xx`)

Step 1 -- Backend instance state (cloud fact, `ecs DescribeInstances`):
any backend not `Running` fails health checks first. Resolve that before
anything else (instance start/stop issues belong to the instance-state
tier if the instance cannot be started).

Step 2 -- Security-group bindings (cloud fact): the script lists which
security groups are associated. Whether those groups actually permit the LB
health-check source ranges is a RULE question owned by the access-blocking
tier (candidate sibling; see `references/slb-backend-diagnosis__handoff-playbook.md`); this script
only screens the association fact. Common misconception: "the security group
allows the port, so the health check must pass" -- a listening service and a
correct route are still required.

Step 3 -- Is a process listening on the health-check port? (customer-run):

```
ss -ltnp            # Linux (or: netstat -ltnp)
netstat -ano        # Windows: find LISTENING on the port, map the PID
```

The customer returns the output verbatim; the entry script parses it with
`--ss-output`. No listener on the port -> the failure is on the instance:
start/fix the service (application-level; the web-service runtime tier or
the customer's own operations handle it).

Step 4 -- Port mapping consistency (console fact): listener backend port
(or health-check port when configured separately) must equal the port the
application actually listens on. A real ticket moved an HTTPS listener's
backend port from 443 to 80 because the migrated Nginx only served plain
HTTP on 80. Console self-check items are listed in the script output
(SELF_CHECK section) -- the customer reads them and returns the values; the
script compares them deterministically with `--backend-port` /
`--health-check-port`.

Step 5 -- Local probe response shape (customer-run):

```
curl -v http://127.0.0.1:<backend-port>/
curl -v -H "Host: <served-domain>" http://127.0.0.1:<backend-port>/<health-check-uri>
```

Returned with `--probe-output`, classified deterministically:

| Observed | Rule | Meaning |
|---|---|---|
| `curl: (52) Empty reply from server` | `HC-EMPTY-REPLY` | Connection accepted but the app closed it without an HTTP response: default vhost mismatch, HTTP/HTTPS mix-up on the port, or a server_name-dependent config (seen after migrations that kept old-domain rewrites) |
| `curl: (7) ... Connection refused` | `HC-NOT-LISTENING` | Nothing listening on that port |
| `< HTTP/1.1 4xx` | -- | App rejects direct-IP or empty-`Host` probes: add a default server block or set the health-check URI to a route that answers 2xx for such probes |
| `< HTTP/1.1 404` | `E404-ROUTE-MISSING` | Service answers but the route/path is missing (see the 404 branch below) |
| `< HTTP/1.1 5xx` | `E502-BACKEND-UNHEALTHY` | App-level failure; collect app error logs (customer-run) |

Step 6 -- LB-side capability constraints (rule calibers; console facts):

- `ALB-BASIC-HTTPS-BACKEND`: ALB Basic edition with an HTTPS listener does
  not support a server group whose backend protocol is HTTPS -- full-chain
  HTTPS forwarding fails (ticket-sourced caliber; official doc pending).
  Fix direction (customer action): switch the backend protocol of the server
  group to HTTP, or upgrade the ALB edition.
- `E404-ROUTE-MISSING`: a 404 through the LB usually means the traffic
  reached the WRONG backend service: verify which backend port the listener
  forwards to and which application (and which routes) actually listens on
  that port -- e.g. a real ticket forwarded HTTPS traffic to a container
  gateway on port 8000 that had no `/mqtt` route, while the reverse proxy
  serving `/mqtt` listened on 443.

If the tree still does not converge: hand off to a human ticket WITH the
evidence list (the script prints it), including all `[WARN]` degradations.

## 502 vs 404 quick routing

- 502 -> the LB could not get a valid response from any healthy backend:
  work the tree from Step 1; most tickets end at Step 3 (nothing listening)
  or Step 5 (app error / empty reply).
- 404 -> some backend DID answer HTTP, but not the expected route: work
  Step 4 (port mapping) and Step 6 (wrong backend service / edition limit).
- "WebSocket handshake: Unexpected response code: 404" -> same as 404, on
  the WebSocket upgrade path; verify the exact path is proxied on the port
  the listener forwards to.

## Continuous monitoring advice (verified doc)

Suggest the customer set up site-availability monitoring and alerting so
health regressions are caught before customers do:
https://help.aliyun.com/zh/ecs/user-guide/monitor-and-alert-on-websites.md

## Cited documents (verified links only)

- Website monitoring and alerting: https://help.aliyun.com/zh/ecs/user-guide/monitor-and-alert-on-websites.md

All other calibers are ticket-sourced; say so when relaying and never
attach unofficial URLs.
