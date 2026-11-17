# Real Client IP Retrieval (Scenario C)

Scope: "the backend logs always show the load balancer's IP / 127.0.0.1
instead of the real client IP", "we enabled X-Forwarded-For but still cannot
get the real IP".

The FIRST question is never "how to configure XFF" -- it is "what does the
link actually look like". Different link shapes have different mechanisms,
and applying the wrong document is the most common root cause in this
scenario (a real ticket followed the CLB layer-7 guide on a machine that had
NO load balancer at all).

> Source discipline: mechanism calibers below are distilled from real
> support tickets of this tier; official SLB/ALB/NLB real-client-IP
> documentation URLs are PENDING verification. Cite only the verified links
> at the bottom.

## Step 1 -- Identify the link shape (customer-declared + console self-check)

This skill cannot read load-balancer configuration from any API; the shape
comes from what the customer states and returns from their console:

| Link shape | Real client IP mechanism |
|---|---|
| Direct client -> ECS (no LB, no proxy) | The app sees the true peer address; if it does not, the problem is app-level, not cloud-level |
| Local reverse proxy only (e.g. Nginx -> IIS on the SAME server, no cloud LB) | NOT a CLB/ALB scenario. The proxy must add a forwarding header and the final app must read it (see Step 3). Do not apply CLB documentation |
| CLB / NLB layer-4 listener (TCP/UDP) | No rule ID: the layer-4 branch has no RULES entry (the entry script prints it as inline text). A layer-4 path carries no HTTP headers, so X-Forwarded-For cannot work. The supported mechanism for layer-4 links is documented in the official SLB real-client-IP docs (URL pending verification -- state the caliber, do not invent the link). Also verify whether the backend reads the peer address correctly, which is the backend-parsing half of rule `RIP-L7-XFF` |
| CLB / ALB layer-7 listener (HTTP/HTTPS) | The LB adds `X-Forwarded-For`; the backend web server/application must be configured to READ it (Step 3) |

Console self-check items for the customer: listener protocol per port (SLB
console -> Listeners), whether the "obtain real client IP" related options
are enabled on the ALB listener, and the backend log format actually in use.

## Step 2 -- Common misconceptions to call out

- "We enabled the real-client-IP feature on the ALB, so the backend gets it
  automatically" -- the LB only puts the address into the header; the
  backend still has to parse and log that header (rule `RIP-L7-XFF`).
- "The CLB layer-7 document applies to my Nginx->IIS setup" -- if there is
  no cloud LB in the path, CLB docs do not apply (rule
  `RIP-NO-LB-LOCAL-PROXY`).
- Test environments that bypass the LB behave differently from production
  ON PURPOSE -- that difference is the evidence that the LB path is where
  the header must be handled.

## Step 3 -- Backend parsing configuration (customer-executed steps)

Guidance only; the customer applies and returns results:

- Nginx: use the real-IP module parameters -- `set_real_ip_from <LB or
  proxy CIDR>;` `real_ip_header X-Forwarded-For;`
  `real_ip_recursive on;` -- and include `$http_x_forwarded_for` (or the
  rewritten `$remote_addr`) in the `log_format`. Reload Nginx.
- Apache: enable/configure the remote-IP module to trust the proxy and read
  `X-Forwarded-For`.
- IIS: the standard access log records the direct peer; to log the value
  from the header, add the `X-Forwarded-For` server variable as a logging
  field (IIS Manager -> Logging -> Select Fields -> Add server variable), or
  have the front Nginx write the header into a field IIS logs. Background
  on IIS deployment:
  https://help.aliyun.com/zh/ecs/user-guide/quickly-purchase-a-windows-instance-and-build-an-iis-service.md
- Application frameworks: configure the trusted-proxy list so the framework
  accepts the forwarding header from the LB/proxy address range only.

## Step 4 -- Re-verification (customer-executed)

The customer sends one test request through the production entry point and
returns the backend log line. Expected: the log shows the real client
address (from the header), not the LB address and not 127.0.0.1. The entry
script records the returned facts (`--customer-message` with the result);
this skill never claims success without that returned evidence.

## Escalation

If the link shape is confirmed as a cloud LB, the backend parsing is
configured correctly, and the header still arrives wrong or missing: hand
off to a human ticket with the evidence list (link shape, listener
protocol, backend config returned, sample log lines) -- platform-side
header behavior can only be confirmed by humans.

## Cited documents (verified links only)

- IIS on Windows background: https://help.aliyun.com/zh/ecs/user-guide/quickly-purchase-a-windows-instance-and-build-an-iis-service.md

All other calibers are ticket-sourced; official real-client-IP doc links are
pending verification -- never invent a URL.
