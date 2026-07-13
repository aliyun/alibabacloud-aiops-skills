# Concurrent Users Triage & SKU Mapping Guide

> This file addresses: how to ask about simultaneous users, how to map to SKU, when to upgrade.
> Product specs & pricing → the SKU matrix (see SKILL.md references)

---

## ECS User-Facing Wording Rules

- **Never mention c9i / g9i / r9i series names** — only say "ECS 2-core 4 GB" or "ECS 4-core 8 GB"
- Analogy script (zh-CN, English: "The recommended ECS is latest-gen, like the newest iPhone — best performance"):

```text
推荐的是最新代 ECS，就像最新款 iPhone，性能最好
```

- Scaling script (zh-CN, English: "If it's not enough later, you can one-click upgrade or add a second instance for load balancing"):

```text
后续不够用可以一键升配，或加一台做负载均衡
```

---

## Standard Phrasing for Simultaneous Users

**Sample output (zh-CN):**

```text
「高峰期那一分钟内，大概会有多少人同时打开你的产品？」
```

(English: "During the peak minute, roughly how many people will have your product open at the same time?")

**Why this phrasing:**
- "Simultaneous" alone is too vague — user interpretations range from "per-second concurrency" to "daily active users," spanning orders of magnitude
- "Peak minute" focuses the user on true peak load; 99% of OPC products peak at a few dozen
- Never use QPS / concurrency / TPS or other technical terms
- Never use Taobao/Double-11 as anchors (irrelevant for OPC)

---

## Simultaneous Users → SKU Mapping Table

| Everyday-Life Anchor (instantly understandable) | Peak-Minute Users | Map to SKU | ECS | RDS |
|-------------------------------------------------|-------------------|------------|-----|-----|
| WeChat Moments likes / small group simultaneously active | ≤15 | **lite_seed** | `ecs-c9i-2c4g` | `rds-1c2g` |
| Xiaohongshu viral post — hottest minute | 15–80 | **lite_growth** | `ecs-c9i-2c4g` | `rds-2c4g` |
| Top influencer livestream — first minute | 80–200 | **lite_traction** | `ecs-c9i-4c8g` | `rds-4c8g` |
| 200+ steady | 200+ | **pro_steady** | `ecs-c9i-4c8g` ×2 | `rds-4c8g-ha` |
| 200+ burst spikes | 200+ burst | **pro_burst** | `ecs-c9i-8c16g` ×2–3 | `rds-4c8g-ha` |

---

## Second-Clarification Rules (mandatory when answer is high or spans tiers)

| User's Initial Answer | Assessment | Follow-up Script |
|----------------------|------------|------------------|
| `一千人同时 / 几千人` ("a thousand / thousands at once") | Almost certainly confusing cumulative with concurrent | `"你说的一千人是一天累计有这么多人来用，还是高峰那一分钟同时打开有这么多？"` |
| `同时一两百` ("one or two hundred simultaneously") | Top-influencer-livestream level — rare for OPC | `"是一天总共这么多还是高峰那一分钟同时打开？"` |
| `几十` ("a few dozen") | Tier-spanning (teens = seed, high-dozens = growth) | `"'几十'跨档——十几个用 seed 够，大几十要升 growth。能具体一点吗？"` |

---

## Post-Mapping Scaling Reminder

> Start with the recommended spec for two weeks, monitor CPU and memory utilization — if sustained >70%, one-click upgrade (e.g., 2-core 4 GB → 4-core 8 GB) or add a second instance for load balancing. ECS supports live migration with zero downtime.

---

## Out-of-OPC-Scope Boundaries

| User Description | Reason | Output |
|-----------------|--------|--------|
| Running Whisper locally / self-hosted LLM | Requires GPU | `"超出 OPC 套餐范围，建议看阿里云 PAI 或 GPU 实例方案。"` |
| "We're a 50-person company / have a dedicated tech team" | Not a one-person company | `"本推荐面向一人公司，建议看阿里云企业级方案。"` |

---

## Upgrade Trigger Signals

### Starter → Lite

- Evolves from "a few friends trying it" to "dozens of people using it consistently"
- Data sensitivity increases: payments/billing/privacy data — SQLite becomes insufficient
- ECS Economy e 2-core 2 GB resource contention — lag/disconnects

### Within Lite (internal upgrades)

- seed → growth: peak rises from teens to dozens, or RDS CPU sustained >70%
- growth → traction: ECS CPU sustained >70% (DB already upgraded, compute layer's turn)

### Lite → Pro

- Single 4-core 8 GB still insufficient → need dual instances + ALB + HA RDS
- Business cannot tolerate downtime: "one instance down = total outage" risk → need high availability
- Token Plan usage is NOT a reason to upgrade to Pro (Token upgrades independently, unrelated to architecture)
