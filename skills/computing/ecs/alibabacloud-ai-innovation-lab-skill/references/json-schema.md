# ai-innovation-lab.json — Structure Documentation

Offline snapshot of Alibaba Cloud's "AI Innovation Lab" (https://www.aliyun.com/daily-act/ecs/ai-innovation-lab). When the `ai-innovation-lab` skill's `fetch_ai_lab.py` cannot fetch the live page (network error / DOM redesign / parsing returns 0 items), it automatically falls back to this JSON. Can also be explicitly forced via `python fetch_ai_lab.py --use-oss`.

Live URL: `https://ai-innovation-lab.oss-cn-beijing.aliyuncs.com/ai-innovation-lab.json` (public read, write restricted to operations RAM sub-account).

## Top-Level Structure

```jsonc
{
  "meta":     { ... },   // Metadata & recommendation order
  "projects": [ ... ]    // 26 project cards
}
```

## meta Fields

| Field | Type | Description |
| --- | --- | --- |
| `schema_version` | string | Currently `"2.0"`. Bump major on breaking changes. |
| `source_url` | string | Data source page URL. |
| `totals.total` | int | Total project count. |
| `totals.by_parent_tab` | object | Count split by first-level Tab: `{ "近30天上新": N, "往期精选": M }`. |
| `recommend_order` | string[] | **Recommendation order lock**: 4 `project.id` values (in original page order). `SKILL.md` uses this array to select the top 4 projects for display, decoupled from `projects[]` physical order. When adding a new project to recommendation slots, only modify this array. |

## projects[] Fields

Each project:

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | **Primary key**, globally unique. Three-tier fallback: ① ComputeNest products use `service-xxx`; ② Developer community scenarios use `scenario-xxx` / `university-xxx`; ③ Solutions/articles use `tech-solution-xxx` / `article-xxx`. |
| `title` | string | Project card title (including Chinese subtitle). |
| `description` | string | One-liner description. |
| `tags` | string[] | Page badge original text, typically containing capability words + `GitHub xxK+` + difficulty. |
| `difficulty` | string \| null | `初阶` / `中阶` / `高阶`, extracted from tags. |
| `github_stars` | string \| null | e.g., `"76K+"`, extracted from tags; null if absent. |
| `parent_tab` | string | First-level Tab: `近30天上新` or `往期精选`. |
| `section` | string | Sub-category (`AI 办公` / `AI 编程` / `设计创作` …), falls back to `parent_tab` if absent. |
| `deploy` | object | Deployment entry, see below. |
| `rank_hint` | int \| null | Only projects updated in last 30 days have values, 1-based page order number. `往期精选` are all null. |
| `is_featured_recent_30_days` | bool | Whether updated in last 30 days. Equivalent to `parent_tab === "近30天上新"`. |

### projects[].deploy Sub-object

| Field | Type | Description |
| --- | --- | --- |
| `url` | string | Full "立即体验" link, output as-is, **preserve all query parameters**. |
| `type` | string | Deployment type enum: `computenest` / `developer-scenario` / `tech-solution` / `developer-article` / `other`. |
| `service_id` | string \| null | ComputeNest product ID, e.g., `service-3a7d40a74d2f4d29b633`. |
| `scenario_id` | string \| null | Developer community scenario/university ID, e.g., `scenario-311001720706`. |
| `region` | string \| null | ComputeNest deployment region, e.g., `cn-hangzhou`. |
| `utm_content` | string \| null | Marketing tracking code, e.g., `g_1000414807`. |

## Field Usage Conventions

1. **Recommendation slots follow `meta.recommend_order`**. When the skill renders, it takes projects in this array's order, not by `projects[]` physical order.
2. **Statistics follow `meta.totals`**. The statistics sentence in SKILL.md `📊 累计收录 N 个项目（近30天上新 X 个、往期精选 Y 个）` reads directly from `totals.total` / `totals.by_parent_tab`.
3. **Do not expose data source in user responses**. Even when from OSS snapshot, present with the same rhetoric as the live page.
4. **ID immutability**: The same project maintains a stable ID regardless of page position changes (service_id / scenario_id / content hash are all stable). This serves as an anchor for downstream analytics / subscriptions / A/B experiments.
5. **New project onboarding process**:
   - Append complete record to `projects[]` (id must be fresh and unique)
   - Increment `meta.totals.total` and corresponding `by_parent_tab` count by +1
   - If the project should enter recommendation slots → add the id to `meta.recommend_order` (simultaneously remove the replaced old id, keeping length = 4)
6. **Write permission convergence**: OSS bucket ACL = public read + authenticated write. Anonymous PUT will be rejected with AccessDenied. Only operations RAM sub-account + ossutil/SDK can update, ensuring all clients read the same trusted data.

## Where is Freshness Metadata?

`fetched_at` / `fetched_by` / `ttl_hours` / `next_refresh_at` and similar **fetch process information** are intentionally not included in the JSON — consumers (fetch_ai_lab.py / end users) don't need them, stuffing them into the contract would bloat the data, and they could easily become "lying fields" inconsistent with actual update times.

When this information is needed, obtain it as follows:

- **Data update time** → Read the OSS object's `Last-Modified` HTTP response header: `ossutil stat oss://ai-innovation-lab/ai-innovation-lab.json` or `curl -I <url>`.
- **Fetch tool version / next refresh time** → Written to OSS object user metadata during upload via `--meta`:
  ```
  ossutil cp ai-innovation-lab.json oss://ai-innovation-lab/ai-innovation-lab.json \
    --meta "x-oss-meta-fetched-by:fetch_ai_lab.py@1.4.0#x-oss-meta-next-refresh:2026-07-02T18:00:00+08:00"
  ```
  Then read with `ossutil stat`, one command for operations, without polluting the external contract.
- **Refresh cycle** → This is operations cron configuration (weekly fetch and upload), not a data property. Keep it in the operations repo or cron metadata.
