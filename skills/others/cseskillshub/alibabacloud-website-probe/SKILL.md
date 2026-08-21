---
name: alibabacloud-website-probe
description: |
  Multi-region website availability probing and nationwide multi-ISP network
  testing over a public probing platform (HTTP / Ping / DNS / MTR /
  traceroute), with an optional mobile 4G/5G perspective. Use when a site or
  API is unreachable from some regions or carriers, loads slowly, shows high
  latency or packet loss, returns HTTP 4xx/5xx unevenly across regions,
  resolves differently by region (DNS hijacking / pollution), misbehaves on
  mobile networks, or when CDN 5xx failures need regional isolation.
  Triggers: "multi-region website availability probing",
  "nationwide multi-ISP HTTP/Ping/DNS/MTR/traceroute testing",
  "website unreachable from some regions or carriers",
  "slow page load / high latency / packet loss",
  "HTTP 4xx/5xx regional isolation",
  "DNS resolution differs by region / DNS hijack pollution",
  "mobile 4G/5G access issue", "CDN 5xx regional isolation".
---

# Network Probe (Multi-Region Public Probing)

Multi-region availability probing over a single public probing backend
(`boce.aliyun.com`). Run HTTP / DNS / Ping / MTR / traceroute tests from
dozens of probe nodes spanning all major regions and the three nationwide
carriers, typically returning within ~30-40 seconds. No account, no login,
no cloud credentials of any kind.

## Overview

| Backend | Platform | Latency | Node Coverage | Purpose |
|---------|----------|---------|---------------|---------|
| **boce (only layer)** | Public probing platform boce.aliyun.com | ~30-40s | Nationwide, three major carriers + limited overseas | Confirm whether a fault exists and whether it is global, regional, or carrier-specific |

Supported probe types: HTTP(S) web probing, DNS resolution checks, Ping,
MTR, traceroute. All probes can optionally run from mobile 4G/5G
perspective nodes (`--mobile`) instead of IDC backbone nodes.

## Execution Principle

- **Read-only**: this skill only submits one-shot probes and reads results;
  it never modifies any configuration.
- **Only the four scripts under `scripts/` may be executed**:
  `boce_wrapper.py`, `boce_tool.py`, `analyze_boce_http.py`,
  `analyze_boce_dns.py`. Ad-hoc probing of result JSON fields is forbidden:
  HTTP and DNS results are interpreted by the two `analyze_boce_*.py`
  scripts; Ping / MTR / traceroute results are interpreted from the per-node
  table that `boce_wrapper.py` prints itself.
- **Results must be persisted to JSON on disk** via the long-form `--output`
  flag (never the `-o` short form), then read through the reader above.
  Never rely on stdout alone.
- Probe only the target explicitly given by the user; never add, expand, or
  substitute probing targets.

## Credentials

**None required.** This skill does not invoke any Alibaba Cloud OpenAPI.
All probing goes through the public platform `boce.aliyun.com`, which is
login-free: the scripts acquire an anonymous web session automatically.
Do not ask the user for any account, AK/SK, STS token, or environment
credential. See [references/ram-policies.md](references/ram-policies.md).

## Input Parameters

Collect from the user:

| # | Input | Required | Notes | Example |
|---|-------|----------|-------|---------|
| 1 | **Target URL / domain / IP** | Yes | The probe target | `https://www.example.com` |
| 2 | Probe type | Inferrable | Infer from the user's wording (see decision table below) | HTTP / DNS / Ping / MTR / traceroute |
| 3 | Probe nodes | Inferrable | Default: nationwide mix across the three major carriers; narrow with `--regions` / `--isp` when the user names regions or carriers (values are the platform-native region/carrier tokens, e.g. the tokens for China Telecom / China Unicom / China Mobile, East China / South China / ... / Overseas) | 15 nodes, all carriers |
| 4 | Mobile perspective | Optional | Add `--mobile` when the user mentions mobile phones, 4G, or 5G | `--mobile` |

Probe type decision table:

| User says | Probe type |
|-----------|------------|
| "probe this URL", "can the site be opened", "status code", "regional access" | HTTP |
| "check DNS", "resolution differs by region", "DNS hijack / pollution" | DNS |
| "ping it", "latency", "packet loss", "is it reachable" | Ping |
| "route trace", "where does it break on the path" | MTR or traceroute |

**Summary**: the user only needs to provide the target; everything else can
be inferred.

## Probe Commands

All commands use relative paths from the skill directory.

### HTTP wide-area probing

```bash
# HTTP wide-area probe (15 nodes, all three major carriers, ~30-40s)
python3 scripts/boce_wrapper.py http \
  --target "https://<domain>/<path>" \
  --max-nodes 15 \
  --output /tmp/boce_http.json

# Analyze the results (dedicated script; ad-hoc field probing forbidden)
python3 scripts/analyze_boce_http.py /tmp/boce_http.json
```

### Mobile perspective (add when the user mentions phone / 4G / 5G)

```bash
python3 scripts/boce_wrapper.py http \
  --target "https://<domain>/<path>" \
  --max-nodes 10 --mobile \
  --output /tmp/boce_http_mobile.json

python3 scripts/analyze_boce_http.py /tmp/boce_http_mobile.json
```

### DNS verification (add when dig results are in doubt)

```bash
python3 scripts/boce_wrapper.py dns \
  --target <domain> \
  --output /tmp/boce_dns.json

# --expected: authoritative/expected A-record IPs, comma-separated
python3 scripts/analyze_boce_dns.py /tmp/boce_dns.json --expected <expected A-record IP>
```

### Ping / MTR / traceroute

```bash
# Ping: per-node average / min / max RTT and packet-loss rate
python3 scripts/boce_wrapper.py ping --target <IP-or-domain> \
  --max-nodes 15 --output /tmp/boce_ping.json

# MTR: per-hop loss and latency along the path from each probe node
python3 scripts/boce_wrapper.py mtr --target <IP-or-domain> \
  --max-nodes 5 --output /tmp/boce_mtr.json

# traceroute: hop-by-hop RTT of the full path
python3 scripts/boce_wrapper.py traceroute --target <IP-or-domain> \
  --max-nodes 5 --output /tmp/boce_tr.json
```

These three types have no dedicated analyze script: the wrapper prints the
per-node table (RTT / packet loss for Ping, per-hop TTL / loss / avg RTT for
MTR and traceroute) after writing the JSON, and that printed table is the
only permitted reading of the results. MTR and traceroute are slower per
node, so keep `--max-nodes` small (~5) for them.

## Probe Budget (mandatory defaults)

A single probe round takes ~15-40s and a full diagnosis should finish within
about 10 minutes. Apply these budgets unless the user explicitly asks for
wider coverage:

| Probe type | Default `--max-nodes` | Rounds per diagnosis |
|---|---|---|
| HTTP (IDC backbone) | 10 | at most 2 (target + one follow-up) |
| HTTP (`--mobile`) | 6 | at most 1; mobile nodes return sparsely, expect partial results |
| DNS | 8 | at most 1 (add only when resolution is in doubt) |
| Ping | 12 | at most 1 |
| MTR / traceroute | 3 | only when a path problem is suspected; slowest type |

Never pad a diagnosis with "while at it" extra rounds to look thorough:
more nodes cost wall-clock time without adding conclusion power beyond the
regional/carrier split these defaults already provide.

## Result Triage

| Probe result | Conclusion | Follow-up action |
|--------------|------------|------------------|
| All nodes normal (HTTP 200 / Ping OK) | Recovered or intermittent | Report the conclusion directly |
| All nodes abnormal (timeout / refused / error) | Globally unreachable | Continue other diagnostic steps |
| Some regions/carriers abnormal, others normal | Regional fault or carrier scheduling issue | Conclusion established; report affected scope |
| All nodes return HTTP 4xx/5xx | Domain reachable but HTTP error | Proceed to status-code diagnosis |
| All nodes errorCode=614 | DNS pollution / anti-fraud interception | Carrier-side problem; advise the user accordingly |
| Probe platform execution failed (platform unavailable) | Cannot confirm from wide-area probing | Degrade to local single-point dig/curl verification (see Fallback) |
| All nodes normal but the user still reports failure | Wide coverage insufficient | Re-run with more nodes or `--mobile`; supplement with local dig/curl |

## Fallback

If the public probing platform is unavailable (session or API failure),
degrade to **local single-point verification** with `dig` and `curl`:

```bash
dig +short <domain> A
dig <domain> @223.5.5.5 +short        # public resolver cross-check
curl -sSvo /dev/null -w '%{http_code} %{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer} %{time_total}\n' "<target URL>"
```

**MANDATORY FALLBACK DISCLAIMER (no exceptions).** Whenever any local
single-point verification (`dig` / `curl`) is used — whether as the primary
evidence after a platform failure or as supplementary evidence after
abnormal probing results — the final report **MUST contain an explicit
disclaimer using these exact phrases** (keep them verbatim, answer in the
user's language and provide the corresponding phrasing in it too):

> Local dig/curl verification is single-vantage-point evidence and cannot
> prove or disprove regional differences.

Requirements:
- The disclaimer must appear in **every deliverable that carries the
  conclusion**: the final conversational reply itself AND any report file
  written to disk (e.g. `outputs/*report*.md`). Putting it only in the
  report file while the final reply states a bare conclusion is a violation
  (request_id=7607: the disclaimer existed in the report file but the final
  reply stated a global outage conclusion without it).
- Any conclusion drawn from local verification (including "globally
  unreachable") **MUST carry this caveat in the same statement or an
  adjacent one**; never state such a conclusion as a proven fact without it.
- This applies even when every probe failed: the correct structure is
  "probing platform returned no usable results + local single-vantage-point
  verification results + the disclaimer above" — never a bare global
  conclusion without the disclaimer.

## Observability

- **User-Agent template (mandatory)**: every request issued by the scripts
  carries a User-Agent built from the template
  `AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}`, where `{SKILL_NAME}`
  is this skill's frontmatter name — `alibabacloud-website-probe` — and
  `{session-id}` is the session identifier described below. Resolved example:
  `AlibabaCloud-Agent-Skills/alibabacloud-website-probe/4eefc3a1be2102b3eb41463c84e98e9b`.
- **session-id rule**: generated **once per session**, as a **32-char
  lowercase hex** string, and kept **consistent across CLI / SDK / Terraform**
  and any other backend touched in that session. The value is cached for the
  whole run (`get_run_session_id()` in `scripts/boce_tool.py`) so that every
  request of one session reports the same id; it may be pinned externally via
  the `SKILL_SESSION_ID` environment variable, which is honoured only when it
  already is a valid 32-char lowercase hex string.
- This User-Agent is the only tracing marker this skill injects. The skill
  calls **no Alibaba Cloud OpenAPI**, so no STS assumption applies and the
  probing backend stays anonymous; the same UA template and session-id rule
  are still enforced on every outbound request.

## Constraints

- **Read-only**: one-shot probes and result retrieval only.
- **Strictly on-demand probing**: probe only the target the user explicitly
  specified; never probe additional targets "while at it".
- **No recreation on failure**: if some nodes fail or time out, analyze the
  results already returned; do not resubmit new probe tasks unless the
  parameters were clearly wrong and the user agrees.
- **Persist results**: all probe results must be written to JSON via the
  long-form `--output` flag; HTTP and DNS analysis must go through
  `analyze_boce_http.py` / `analyze_boce_dns.py`, while Ping / MTR /
  traceroute are read from the wrapper's own printed table.
- **Fallback disclaimer is mandatory**: whenever local dig/curl
  single-point verification is used, the final report MUST state — using the
  exact wording from the Fallback section (and its faithful phrasing in the
  answer's language) — that it is single-vantage-point evidence and cannot
  prove or disprove regional differences; a global conclusion without this
  caveat is forbidden.
- `--mobile` pre-filters known-invalid city+carrier combinations
  (built-in blocklist embedded in `scripts/boce_tool.py`) to save ~15-20% runtime.

## Deep Diagnosis Rules

When probes return errors or anomalies, the agent **must** load
[references/diagnostic-rules.md](references/diagnostic-rules.md) and follow
its three-step flow. Vague conclusions such as "network error" or
"operation timeout" are forbidden; every judgment must cite concrete result
fields as evidence.

## User Guidance

When the user asks exploratory questions ("what can this skill do?", "how
do I use it?"), load
[references/user-guide.md](references/user-guide.md) and answer based on it.
Do not copy user-guide.md content into SKILL.md.

## Important Notes

- Probe runs take ~30-40s per round; follow the Probe Budget defaults so a
  full diagnosis finishes within ~10 minutes; two follow-up rounds take
  ~1-2 minutes total.
- Mobile probe nodes are scarce and the platform often returns only a
  fraction of submitted mobile nodes (e.g. 1-2 out of 10): treat partial
  mobile results as directional evidence, never wait for or resubmit to
  collect the full node list.
- The platform assigns no shareable web link to API-submitted probes; the
  `taskId` printed by the wrapper is for local traceability only.
- Overseas coverage is limited; prefer nationwide conclusions and state the
  coverage boundary when the user asks about overseas access.

## Examples

### Example 1: Regional HTTP fault isolation

User: "Users in some provinces say https://www.example.com returns 502,
please check the scope."

```bash
python3 scripts/boce_wrapper.py http \
  --target "https://www.example.com" \
  --max-nodes 15 \
  --output /tmp/boce_http.json
python3 scripts/analyze_boce_http.py /tmp/boce_http.json
```

Reading: status-code distribution shows `200(12), 502(3)` and the abnormal
nodes share one province + one carrier → regional / carrier-scoped fault,
not a global outage. Report the affected scope and the distinct
`targetIp` of failing nodes as evidence.

### Example 2: DNS hijacking verification

User: "www.example.com resolves to a strange IP for some users, the
authoritative IP is 1.2.3.4."

```bash
python3 scripts/boce_wrapper.py dns \
  --target www.example.com \
  --output /tmp/boce_dns.json
python3 scripts/analyze_boce_dns.py /tmp/boce_dns.json --expected 1.2.3.4
```

Reading: the analyzer splits nodes into ok / polluted-overseas /
polluted-invalid (0.0.0.0 or 127.x) / partial / empty and prints the
carrier distribution of polluted nodes. Pollution concentrated on one
carrier with `errorCode=614` → carrier-side DNS hijacking / interception.
