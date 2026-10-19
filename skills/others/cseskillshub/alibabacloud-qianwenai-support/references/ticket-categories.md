# Ticket Categories Reference

> **Do not hardcode category IDs.** Always fetch the latest list with:
> ```bash
> qianwen support create --list-categories --format json
> ```
>
> This file is for keyword matching guidance only. The category set changes
> over time; the API is the single source of truth for IDs.

## Keyword-to-Category Mapping

Use these English keywords to select the best category from the dynamic list.
When the customer writes in another language, translate the intent into the
closest English keyword before matching; never persist the customer's original
wording in the category lookup.

| Keywords | Likely Category |
|----------|----------------|
| usage, billing, quota, tokens, cost, charge, invoice | Usage and Billing |
| API, SDK, call failure, timeout, error, 401, 403, 429, 500 | API Issues |
| how to, tutorial, guide, feature, capability | Feature Guide |
| purchase, price, pricing, plan, subscribe | Purchase and Pricing |
| refund, cancel, unsubscribe | Refund and Cancellation |
| permission, account, login, console | Account and Console |
| documentation, docs, missing | Documentation |
| security, violation, content, safety | Safety and Compliance |
| MiniMax, Kimi, third-party | Third-party Models |
| discount, promotion, campaign | Promotions |
| OpenClaw, Cursor, integration, connector | AI Tool Integration |
| slow, latency, performance, response time | Performance and Latency |
| concurrency, rate limit, QPS, quota exhausted | Concurrency and Rate Limiting |
| poor quality, inaccurate, hallucination, wrong answer | Model Quality and Accuracy |
| training, fine-tune, dataset | Model Training and Fine-tuning |
| data, privacy, leak | Data and Privacy |
| downtime, outage, unavailable, service interrupted | Service Availability |
| upgrade, version, migration | Upgrade and Migration |
| config, setting, parameter | Configuration |
| other, uncategorized | Other |

## Selection Strategy

1. Run `qianwen support create --list-categories --format json`.
2. Parse the returned category list; treat the API result as authoritative.
3. Match the customer's issue keywords against the table above.
4. If multiple categories match, prefer the more specific one.
5. If nothing matches, use the most generic or "Other" category.
6. Never reuse a category ID across runs; re-fetch every session.
