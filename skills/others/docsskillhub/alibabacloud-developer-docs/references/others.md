# Peripheral knowledge (other script usage / other common entries)

This file is a **background quick reference**, not an execution flow. Answer these questions directly when asked; names and addresses here may change over time — when accuracy matters, verify via the live-lookup entries given below.

## 1. Other usage of the retrieval script

`scripts/aliyun_help.py` is a general-purpose read-only tool for the Alibaba Cloud Help Center + OpenAPI metadata; it works for any product. The table below is a capability reference, not an output list; show only items the user explicitly asks about, place necessary CLI at the end per `SKILL.md` output constraints, and never proactively expose interfaces or internal evidence-gathering commands:

| Usage | Command |
|------|------|
| Query the International site (www.alibabacloud.com / api.alibabacloud.com) | add `--site intl` to any subcommand (e.g., `search "live transcoding" -p live --site intl -L en`) |
| Other corpus languages | `--site <site> -L <language>` (China site supports `zh`/`en`; International site also `tc`/`ja`/`id`/`pt-br`/`fr`) |
| List all documentation products / OpenAPI products | `list-products [keyword]` (from the Help Center navigation menu, includes category IDs) / `api-products [keyword]` |
| Search the official Skill catalog | `skill-search [keyword]` / `skill-info <skillName>` (rules in Official Skill search rules) |
| Query official announcements / parse change impact | `notice-search [keyword] [-p <product-code>] --site <site> -L <language> --full` (rules in Announcement search rules; add `--json` for full text; on no announcement hit, docs are queried by default and both sides shown) |
| Query another product's docs or APIs | switch to its product code (e.g., `api-info oss GetBucketPolicy`); codes in Product code table |
| Pin an API version | add `-V <version>` to `api-list` / `api-info` |
| Adjust timeout / skip the 10-minute result cache | `--timeout <seconds>` / `--no-result-cache` |

- The China and International sites differ in products, regions, and billing; the script **never mixes or falls back across sites**. Once the International site is confirmed, add `--site intl` per the parameter table in `SKILL.md` "Step 1" (`search` / `list-docs` / `read-product` also take `-L <language>`); never apply China-site billing/region conclusions.
- The script is read-only and anonymous: GET for docs/metadata/Skills, form POST for public announcement queries; it never calls user resource APIs or performs changes — resource calls are executed by the user via CLI / server SDKs. Announcement language coverage is in Announcement search rules; it does not follow doc-corpus coverage.
- Full parameters: `python3 scripts/aliyun_help.py <subcommand> -h`.

## 2. Other common entries

Generic entries (replace `<product-code>` with the documentation / OpenAPI product code from the Product code table):

| Entry | China site | International site |
|------|------|------|
| Product doc home | `https://help.aliyun.com/zh/<product-code>/` | `https://www.alibabacloud.com/help/en/<product-code>/` |
| OpenAPI Explorer | `https://api.aliyun.com/product/<OpenAPI-product-code>` | `https://api.alibabacloud.com/product/<OpenAPI-product-code>` |
| `llms.txt` full doc index | `https://help.aliyun.com/zh/<product-code>/llms.txt` | `https://www.alibabacloud.com/help/en/<product-code>/llms.txt` |
| Official Skill catalog | <https://skills.aliyun.com> | <https://skills.alibabacloud.com> |
| Official announcement catalog | <https://www.aliyun.com/notice/> | <https://www.alibabacloud.com/notice/intl/list> |
| Aliyun CLI official docs | <https://help.aliyun.com/zh/cli/> | <https://www.alibabacloud.com/help/en/cli/> |
| RAM console (authorization / AK management) | <https://ram.console.aliyun.com/> | <https://ram.console.alibabacloud.com/> |

Replace `<product-code>` with the actual code; e.g., ApsaraVideo Live is `live` (doc home <https://help.aliyun.com/zh/live/>, OpenAPI Explorer <https://api.aliyun.com/product/live>).

Give the user only the column for the confirmed site (site determination in `SKILL.md` "Step 1: Determine the site"); the `en` in International site doc URLs may be replaced with `zh`/`ja`/`tc`/`id`/`pt-br`/`fr` per the user's language.