# Network Probe Skill - Getting Started

## What This Skill Does

In one sentence: **it lets the AI test a URL from many locations and
carriers at the same time, all over the public internet.**

Imagine you run `www.example.com` and users complain that it "loads very
slowly" or "returns 502". How do you tell whether the problem is
nationwide, or limited to a certain region or carrier?

The traditional way is to log into a probing platform, create tasks
manually, pick nodes, wait, download data, and analyze it row by row —
often 10-20 minutes of work.

With this skill installed, you just say:

> "Probe www.example.com for me"

The AI submits the probes, waits for the results, analyzes the data, and
hands you a diagnosis report. The whole process takes about one or two
minutes.

### Single Public Probing Backend

This skill uses one probing backend: the public platform
`boce.aliyun.com`. It is login-free — no account and no credentials are
needed at all; the scripts acquire an anonymous session automatically.

| Backend | Latency | Node coverage | When to use |
|---------|---------|---------------|-------------|
| **boce** | ~30-40s | Nationwide, three major carriers + limited overseas | Always; the only probing layer |

If the platform itself is unavailable, the AI degrades to local
single-point verification with `dig` / `curl` and says so explicitly.

### What It Can Test

| What you say | What actually runs | Use case |
|--------------|--------------------|----------|
| "ping it" | Ping from many nodes | Latency and packet loss |
| "probe the page" / "HTTP test" | HTTP(S) requests from many nodes | Availability, status codes, load time |
| "check DNS" / "DNS probe" | DNS resolution from many nodes | Verify records, detect hijacking/pollution |
| "route trace" / "MTR" | MTR from many nodes | Find where the network path breaks |
| "traceroute" | Classic traceroute | Lightweight route tracing |
| "mobile" / "phone" / "4G/5G" | Mobile-perspective probes | Reproduce phone / cellular access issues |

### Coverage

- Nationwide nodes across the three major carriers (Telecom, Unicom,
  Mobile), selectable by region or by carrier; mobile 4G/5G perspective
  nodes available via `--mobile`.
- Default node mix: a nationwide sample across all three carriers, enough
  for most situations.

---

## Installation

1. Install the skill package in your agent environment (drag the skill
   file into the skills manager and save).
2. Use it directly — there is nothing to configure. No accounts, no
   passwords, no environment variables.

**Verify the installation**: ask

> "Probe www.baidu.com for me"

If the AI runs the scripts and returns status codes and latency data after
about 30 seconds, the installation works.

---

## Scenario Tutorials

### Scenario 1: Quick HTTP Probe

**Your situation**: you want to confirm whether a domain is reachable from
all over the country, and what status codes come back.

**You say**:

> "Probe https://www.example.com for me"

**What the AI does**:
1. Sends HTTP requests from ~15 nodes (three carriers x multiple regions).
2. Waits ~30 seconds for results.
3. Analyzes status-code distribution, target IPs, and abnormal nodes, and
   gives you a diagnosis report.

**How to read the result**:

```
Status distribution: 200(12), 502(3)
Target IP distribution: 1.2.3.4(12), 5.6.7.8(3)

Abnormal nodes:
  Guangdong Mobile: HTTP 502, IP=5.6.7.8
  Fujian Mobile:    HTTP 502, IP=5.6.7.8
  Hunan Mobile:     HTTP 502, IP=5.6.7.8
```

If most nodes are fine but one carrier/region fails, it is a local fault.
If everything fails, it is a global outage.

**Advanced usage**:

> "Probe https://www.example.com from East China and South China only"

> "Probe https://www.example.com with mobile probes"

---

### Scenario 2: Connectivity Check (Ping)

**Your situation**: you want to know whether a domain/IP is reachable from
everywhere, and what the latency looks like.

**You say**:

> "Ping api.example.com for me"

**What the AI does**:
1. Sends Ping from multiple nodes.
2. Waits ~30 seconds.
3. Reports per-node latency and packet loss.

**How to read the result**:

```
Beijing Unicom:  latency 12ms, loss 0%   OK
Beijing Telecom: latency 8ms,  loss 0%   OK
Beijing Mobile:  latency 35ms, loss 5%   elevated
```

If one carrier shows much higher latency or heavy loss, that direction of
the network has a problem.

---

### Scenario 3: DNS Resolution Verification

**Your situation**: you changed DNS records and want to confirm the
resolution is correct everywhere, or you suspect DNS pollution.

**You say**:

> "Check the DNS resolution of www.example.com"

or:

> "Run a DNS probe for www.example.com; the expected IP is 8.148.151.67"

**What the AI does**:
1. Queries the DNS resolution from multiple nodes.
2. Compares each node's resolved IPs against the expected IP.
3. Flags abnormal nodes (resolution to private addresses, unexpected IPs,
   overseas IPs).

**How to read the result**:

```
Normal nodes: 12/15
Abnormal nodes:
  Beijing Mobile:  resolved to 0.0.0.0 (suspected DNS pollution)
  Guangdong Telecom: resolved to 10.0.0.1 (unexpected IP)
  Shanghai Unicom: resolved to 8.148.151.67 (OK)
```

---

### Scenario 4: Mobile (4G/5G) Access Issues

**Your situation**: users report the site fails or is slow on their phones,
while desktop access looks fine.

**You say**:

> "Probe https://www.example.com from mobile 4G/5G perspective"

**What the AI does**:
1. Runs the same HTTP probe using mobile-perspective nodes (`--mobile`).
2. Compares mobile results with the normal IDC-backbone results.
3. Tells you whether the fault is specific to cellular last-mile access.

---

### Scenario 5: CDN 5xx Troubleshooting

**Your situation**: the CDN returns 502/503/504 and you need to know the
scope and whether the origin is involved.

**You say**:

> "https://www.example.com keeps returning 502; the origin IP is 1.2.3.4.
> Help me check whether it is the origin or the CDN"

**What the AI does**:
1. Confirms the 5xx scope with wide-area HTTP probing (global vs regional).
2. Checks whether failing nodes resolve to a distinct CDN edge IP.
3. Optionally probes the origin locally with curl for a single-vantage
   cross-check, then concludes:
   - 5xx everywhere + origin errors -> origin-side fault
   - 5xx everywhere + origin healthy -> CDN return-to-origin problem
   - 5xx only in some regions -> specific edge nodes / scheduling issue

---

### Scenario 6: Cross-Region Comparison

**Your situation**: you want to compare access quality across regions and
carriers for the same URL.

**You say**:

> "Test https://www.example.com across multiple regions and compare the
> load speed"

**What the AI does**:
1. Runs a multi-node probe with a broad regional spread.
2. Waits ~30-60 seconds.
3. Produces a comparison table of per-node timings.

---

## Talking to the AI

### Things worth stating explicitly

| Element | If you omit it | Example |
|---------|----------------|---------|
| **Target address** | The AI has nothing to test | `www.example.com` or `https://api.example.com/v1/data` |
| **Test type** | The AI infers from your words | "ping" / "probe" / "DNS" / "route trace" |
| **Region / carrier** | Default: nationwide three-carrier mix | "from East China" / "Telecom only" / "nationwide" |
| **Extra info** | Some scenarios need it | Origin IP, expected DNS IP |
| **Device perspective** | Default: IDC backbone | Say "mobile", "phone", or "4G/5G" for the mobile view |

### Ready-to-use sentences

```
Probe https://www.example.com for me

Ping www.example.com for me

Check the DNS resolution of www.example.com

Probe https://www.example.com from East China and South China

Probe https://www.example.com with mobile probes

www.example.com returns 502; the origin IP is 1.2.3.4, help me investigate

Traceroute api.example.com for me

Compare the access speed of https://www.example.com across regions
```

### Notes

- Probing takes time: about 30-40 seconds per round; two follow-up rounds
  take about 1-2 minutes in total.
- If you only give a domain without a test type, the AI usually defaults to
  an HTTP probe or Ping.
- More nodes = longer waiting. The default nationwide sample is enough for
  most cases.
- No login or account handling is needed from you — the backend is
  anonymous.
- Saying "mobile", "phone", or "4G/5G" switches the probes to the mobile
  perspective (4G/5G last-mile view).
