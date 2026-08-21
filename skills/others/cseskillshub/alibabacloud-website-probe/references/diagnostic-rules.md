# Deep Diagnosis Rules (Must-Read for the Agent)

When a probe returns errors or anomalies, the agent **must** follow the
flow below. Surface-level conclusions such as "network error" or
"operation timeout" are forbidden. Every judgment must be backed by
concrete fields from the probe result JSON.

## Principles

- Vague conclusions ("maybe a network issue", "maybe the server is down")
  are forbidden.
- Every judgment must cite concrete field values (`errorCode`,
  `HTTPResponseCode`, `TotalTime`, `HTTPDNSTime`, `tcpConnectTime`,
  `SSLConnectTime`, `targetIp`, `ips`, `failureRate`, `routeJson`, ...).
- Multi-node probes **require cross-node comparison**; never analyze a
  single node in isolation.
- Follow-up probes (DNS / MTR / traceroute) are not optional — once
  launched, their results must all be used in the conclusion.

## Result Field Reference (public probing backend)

Common node fields (HTTP / DNS / Ping / MTR / traceroute):

| Field | Meaning |
|-------|---------|
| `errorCode` | 0 = success; non-zero = probe-level error (e.g. 614 = DNS hijacking / pollution) |
| `message` | Human-readable error description for the node |
| `areaCN` / `provinceCN` / `cityCN` / `ispCN` | Node location and carrier |
| `probeType` | `idc` (backbone) / `mobile` (4G/5G last mile) |
| `targetIp` | IP the target resolved to from this node |
| `ipGeoMap` | JSON string mapping resolved IPs to geo/ISP info (`cnty`, `prov`, `city`, `isp`) |

HTTP-only fields:

| Field | Meaning |
|-------|---------|
| `HTTPResponseCode` | HTTP status code (0 = no response received) |
| `TotalTime` | Total elapsed time (ms) |
| `HTTPDNSTime` / `tcpConnectTime` / `SSLConnectTime` | DNS / TCP connect / TLS handshake time (ms) |
| `dnsSuccess` | Whether node-side DNS resolution succeeded |

DNS-only fields:

| Field | Meaning |
|-------|---------|
| `ips` | A-records resolved by the node (comma-separated) |
| `cnames` | CNAME chain returned by the node |
| `dnsServer` | Recursive resolver actually used by the node |
| `TotalTime` | Resolution time (ms) |

Ping fields: `TotalTime` (avg RTT), `pingMinTime`, `pingMaxTime`,
`failureRate` (packet loss %), `pingReceivedNum`.

MTR / traceroute fields: `sourceIp`, `targetIp`, `routeJson` (list of hops
with `ttl`, `address_to`, `loss`, `snt`, `last`, `avg`, `best`, `worst`) or
`route` (hop list with `ip`, `rtt`).

## Main Diagnostic Flow (Three-Step Method)

All scenarios share this flow:

```
Step 1: Read the error -> classify the failure mode, route to a scenario
Step 2: Read the per-node evidence -> DNS results / HTTP timing / MTR hops
Step 3: Apply scenario-specific rules -> see the scenario sections below
```

### Step 1: Error Type Routing

| Failure mode | Typical evidence | Route to |
|--------------|------------------|----------|
| Slow but successful | HTTP 200 with high `TotalTime` | Scenario A: slow access |
| Connection failure / timeout | `errorCode` non-zero, `HTTPResponseCode` 0, timeout in `message` | Scenario B: access failure |
| HTTP 5xx | `HTTPResponseCode` 502/503/504 | Scenario C: CDN 5xx regional isolation |
| HTTP 4xx | `HTTPResponseCode` 403/404/429 ... | Analyze the status code and scope directly |
| DNS hijacking | `errorCode`=614, or `ips` resolving to unexpected / overseas / 0.0.0.0 / 127.x addresses | Scenario B + DNS evidence |

### Step 2: Per-Node Evidence Checks (all scenarios)

Regardless of scenario, check these three evidence groups:

1. **DNS resolution** (DNS probe: `ips`, `cnames`, `dnsServer`;
   HTTP probe: `targetIp`, `dnsSuccess`):
   - Do resolved IPs match the expected/authoritative records
     (`analyze_boce_dns.py --expected`)?
   - Is any node resolving to 0.0.0.0 / 127.x / unexpected overseas IPs
     (pollution flags `pollution_invalid` / `pollution_overseas`)?
   - Use `ipGeoMap` to attribute unexpected IPs without extra lookups.

2. **HTTP timing decomposition** (HTTP probe):
   - Large `HTTPDNSTime` -> slow resolution (resolver or long CNAME chain)
   - Large `tcpConnectTime` -> slow TCP setup (distance or link quality)
   - Large `SSLConnectTime` -> slow TLS handshake
   - Large `TotalTime` with normal phase times -> server-side processing or
     download slowness

3. **Route evidence** (MTR / traceroute: `routeJson` / `route`):
   - Does the path reach `targetIp`?
   - Where does loss appear (hop-level `loss`)? Loss starting at a specific
     hop and persisting to the end = fault at/behind that hop; loss only at
     intermediate hops with a healthy tail = the hop simply filters probes.

## Scenario A: Slow Access

**Symptom**: HTTP 200 on most nodes but `TotalTime` abnormally high, or
only some regions/carriers report slowness.

Required analysis:

1. **Timing decomposition per node**: compare `HTTPDNSTime`,
   `tcpConnectTime`, `SSLConnectTime`, `TotalTime` across nodes and
   attribute the dominant cost (see Step 2.2).
2. **Cross-node comparison**: sort nodes by `TotalTime`; if only one
   region/carrier is slow, the bottleneck is on that path — run MTR from
   the affected nodes (`boce_wrapper.py mtr`) and locate the loss/latency
   hop in `routeJson`.
3. **Ping correlation**: run Ping on the same target; high `TotalTime` or
   `failureRate` confirms a network-layer problem rather than application
   slowness.
4. **Mobile perspective**: if users report slowness on phones, re-run with
   `--mobile`; compare `TotalTime` between `probeType=idc` and
   `probeType=mobile` nodes.

## Scenario B: Access Failure (timeout / unreachable)

**Symptom**: `errorCode` non-zero, `HTTPResponseCode` 0, or timeout /
connection-refused text in `message`.

Required analysis:

1. **Failure scope classification**:
   - All nodes fail -> target-side problem (server down, port closed,
     cert/TLS failure). Quote the common `errorCode` / `message`.
   - One region or one carrier fails -> regional link fault or
     carrier-side interception. List the affected `provinceCN` / `ispCN`
     set versus the healthy set.
2. **DNS hijacking check**: `errorCode`=614 or resolution to 0.0.0.0 /
   127.x / overseas IPs (`pollution_invalid` / `pollution_overseas` from
   `analyze_boce_dns.py`) means the failure happens before any TCP
   connection; attribute it to the resolver/carrier named in `dnsServer`
   and `ispCN`.
3. **Path evidence**: run MTR from failing nodes; in `routeJson`, locate
   the first hop with sustained `loss` to the end — that is where the path
   breaks. A path that never reaches `targetIp` indicates blackholing or
   upstream filtering.
4. **Local fallback cross-check**: verify the target once locally with
   `dig` / `curl` to separate "target truly down" from "only certain
   vantage points fail".

## Scenario C: CDN 5xx Regional Isolation

**Symptom**: `HTTPResponseCode` 502/503/504 on some or all nodes.

Required analysis:

1. **Scope of the 5xx**: group nodes by `HTTPResponseCode` and correlate
   with `provinceCN` / `ispCN`:
   - 5xx everywhere -> origin or global CDN fault
   - 5xx only in certain regions/carriers -> specific edge nodes /
     scheduling problem
2. **Distinct edge IP check**: compare `targetIp` across failing and
   healthy nodes. If all failing nodes resolve to one IP (or IP set) while
   healthy nodes resolve elsewhere, the bad CDN edge IP is isolated —
   report it with the `ipGeoMap` attribution.
3. **DNS sanity**: confirm failing nodes are not actually polluted
   (`errorCode`=614 / unexpected IPs) before blaming the CDN.
4. **Origin-side cross-check (local)**: if the user provides the origin
   address, probe the origin locally with `curl` (single vantage point) to
   separate origin failure from CDN return-to-origin failure:

   | Wide-area result (via CDN) | Local origin probe | Judgment |
   |--------------------------|--------------------|----------|
   | 5xx | origin 5xx/error | Origin-side fault, CDN passes it through |
   | 5xx | origin 200 | CDN return-to-origin path problem (edge config / origin fetch) |
   | 5xx regional only | origin 200 | Specific edge nodes/scheduling faulty |
   | 5xx | origin unreachable | Origin down or wrong origin IP |

## Cross-Node Comparison (all scenarios)

For any multi-node probe, always:

1. **Group by failure mode**: e.g. group A = 200 but slow, group B =
   network error, group C = 5xx, group D = 614. Different modes =
   different root causes; never merge them.
2. **Correlate with region/carrier**: one city or province only -> link or
   geo-blocking issue; one carrier only -> carrier-side interception; all
   nodes identical -> target-side problem.
3. **Compare timings**: `TotalTime`, `tcpConnectTime`, `SSLConnectTime`
   across nodes expose distance and path-quality differences; for MTR,
   compare hop-level `loss` and `avg` between healthy and failing nodes.

## Diagnostic Report Format

The report must contain (mandatory):

1. **Probe overview table**: one row per node — location/carrier,
   status (`errorCode` / `HTTPResponseCode`), key timings, `targetIp`.
2. **Evidence analysis**: DNS resolution findings (`ips` vs expected,
   pollution flags), HTTP timing decomposition, MTR/traceroute path
   findings (hop where loss starts).
3. **Scenario analysis**: per the routed scenario, include concrete
   evidence (field names and values), the reasoning chain from evidence to
   conclusion, and actionable remediation suggestions.
4. **Cross-node conclusion**: state the blast radius — specific
   region/carrier versus global.
5. **CDN 5xx extra output**: the two-way comparison table (wide-area via
   CDN vs local origin probe) and the isolated bad `targetIp` list when
   applicable.
