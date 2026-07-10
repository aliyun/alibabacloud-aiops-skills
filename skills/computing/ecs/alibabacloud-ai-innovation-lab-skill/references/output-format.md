# Output Format Reference (AI Innovation Lab)

This document provides the **detailed field definitions, statistics rules, selection rules, and layout details** for the main "AI Innovation Lab" response. The main `SKILL.md` already provides the fixed template and trigger actions; this document is for in-depth analysis of aspects that need further clarification.

## Overall Structure (Order Locked)

Responses must follow the ①→②→③→④→⑤ order. **Paragraph positions cannot be swapped**:

```
① 🚀 Welcome intro (fixed copy from Execution Step 1) — must be at the top of the response
② ⚡ Cloud computing one-liner emphasis (fixed copy, use verbatim)
③ 🔗 Official homepage: [AI尝鲜实验室](https://www.aliyun.com/daily-act/ecs/ai-innovation-lab)
④ 📊 累计收录 <total> 个项目（近30天上新 <n_new> 个、往期精选 <n_legacy> 个），为你推荐本周最值得体验的项目

| 项目 | 简介 | 立即体验 |
| --- | --- | --- |
| **<title-1>** | <desc> | [立即体验](<url>) |
| **<title-2>** | <desc> | [立即体验](<url>) |
| **<title-3>** | <desc> | [立即体验](<url>) |
| **<title-4>** | <desc> | [立即体验](<url>) |

⑤ Closing encouragement + 2 friendly questions
```

Historical lesson: Previously placing the welcome intro after the table was explicitly rejected by users. Fixed at position 1.

## Fixed Copy (Use Verbatim, Emoji Must Not Be Omitted)

**Welcome Intro (①)**:

```
🚀 我们每周为您筛选 github 上最值得关注的 AI 开源项目，并为您打包好"开箱即用"的云端环境（告别繁琐配置，无需下载安装包与环境依赖）。无论您是开发者、设计师、产品经理、学生还是 AI 爱好者，都能在这里零门槛畅玩前沿 AI 应用。
```

**Cloud Computing Emphasis (②)**:

```
⚡ 算力全部跑在云端 ECS —— 不挑你的电脑配置、不占本地硬盘、更不用担心装坏系统或误删文件。一杯咖啡的时间，就能拥有一台属于自己的"AI 实验机"。
```

**Official Homepage Link (③)**: Link text is fixed to "AI尝鲜实验室", URL is `https://www.aliyun.com/daily-act/ecs/ai-innovation-lab`. **Do not use bare URLs** — the frontend will render it as a site card `ai-innovation-lab · aliyun.com`, breaking brand consistency.

## Selection Rules (Post-2026-06 New Page)

- Directly take the **first 4 projects by page order** from the `近30天上新` panel, i.e., the first 4 items from `python scripts/fetch_ai_lab.py --format json` output.
- **Maintain page order** — do not reorder by GitHub star / tags / any other field.
- If `近30天上新` has fewer than 4 items, change the content below the statistics sentence to table + closing text "近30天新上 N 个，全在这里啦". Do not pad or pull from `往期精选` to fill.

## Statistics Fields

| Placeholder | Meaning | Source |
| --- | --- | --- |
| `<total>` | Total project count | Sum of the two parent Tab badges from `--summary` output's `parent_tabs` |
| `<n_new>` | Updated in last 30 days count | `parent_tabs["近30天上新"]` |
| `<n_legacy>` | Past highlights count | `parent_tabs["往期精选"]` |

Read badge counts directly — more accurate than visible cards. Use category names as-is from the page (`近30天上新` / `往期精选`), do not rewrite to old names like "AI 提效工具".

## Table Fields

Each project occupies one table row, **keep only** title, description, and link:

```
| 项目 | 简介 | 立即体验 |
| --- | --- | --- |
| **<title>** | <description> | [立即体验](<deploy_url>) |
```

- Do not output tags / difficulty / GitHub star or other fields.
- Do not add subheadings like "为你推荐" — the statistics sentence already contains "为你推荐" semantics, adding a title would be redundant.
- Output `deploy_url` as-is — **do not abbreviate or truncate**.

## Field Meanings (JSON Parsing Reference)

For reference only when parsing script JSON output. **Do not include this table in responses**:

- `title` — Project card title (including Chinese subtitle)
- `description` — Card body one-liner description
- `tags` — Badge array: capability words + `GitHub xxK+` + difficulty (`初阶` / `中阶` / `高阶`)
- `parent_tab` — `近30天上新` / `往期精选` (first-level category)
- `section` — Sub-category (`AI 办公` / `AI 编程` / `设计创作` …), falls back to `parent_tab` if absent
- `view_count` — Deprecated on new page, always 0, do not use for sorting
- `deploy_url` — "立即体验" jump link, output as-is

## Closing Interaction (2 Sentences)

Guide users to reveal their specific use case along two dimensions: "profession / industry / preference", enabling personalized recommendations in the next round. Examples:

- Sentence 1 asks about profession / industry: 「你平时是写代码、做设计、跑运营还是做学生党呀？」
- Sentence 2 asks about interest / problem to solve: 「想偷懒做点什么？比如自动写周报、批量出图、搭个网站，我帮你挑最顺手的那个 👀」

Immediately below the table, first add a fixed encouragement: "挑一个 → 点链接 → 10 分钟玩起来 🎉", then append the two questions above.

## Hover Preview Instructions (For Debugging Only, Do Not Include in Responses)

QoderWork frontend attaches hover preview cards to `[text](url)` Markdown links, fetching the target page's `<title>` / `og:title`. Alibaba Cloud console paths like `computenest.console.aliyun.com` will 302 redirect to the login page when not authenticated, showing "阿里云登录-欢迎登录…" in the preview — this is normal behavior and unrelated to link validity. **Keep Markdown link syntax, do not change to native HTML `<a>`** (user explicitly requested to preserve hover preview behavior).

## Data Source Transparency

When data comes from the OSS snapshot, `--summary` output includes an additional `"source": "oss-fallback"` field for internal differentiation (**for debugging only**), along with `snapshot_meta`. The statistics sentence and response body **maintain the same format as the live page**. **Do not** add source hints like "(data from OSS snapshot)" in user-visible responses — data source should be transparent to users.

The OSS snapshot explicitly locks recommendation order via `meta.recommend_order`. The script sorts projects by this service_id list, so **still take the first 4** as recommendations.
