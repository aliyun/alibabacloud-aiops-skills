# Official Documentation Dynamic Retrieval Strategy (doc-lookup)

This file defines the dynamic retrieval (fetch) strategy for Security Center vulnerability module official documentation, for the agent to execute at the following moments: when the embedded reference documents (SKILL.md and each scenario document) do not cover the user's question, or when the required content belongs to the high-frequency-update category — the official phrasing must be fetched per this strategy first before answering the user.

## When to Trigger Dynamic Retrieval

| Situation | Action |
|------|------|
| Error code not matched in scenario-errors.md's embedded high-frequency error code table | Go directly to the Level 2 direct link (official error code page) to verify |
| User asks about product mechanisms (scan cycle, status transitions, repair limitations, whitelist rules, etc.) not covered by embedded documents | Locate via the Level 1 anchor directory page |
| Need to cite high-frequency-update facts (error code tables, edition capability matrices, billing, OS support lists, EOL schedules) | [MUST] dynamically verify the official page before citing — outputting from memory alone is forbidden |
| Embedded direct link invalid (404 or content mismatch) | Switch to the next-level link per the degradation order |

## Three-Level Retrieval Chain (execute in order; degrade only when the previous level fails)

### Level 1: Anchor Directory Page (first choice)

Fetch the vulnerability management directory page, parse the sub-document URL list in the page, then locate the target document by title keywords:

```
https://help.aliyun.com/zh/security-center/user-guide/vulnerability-management/
```

| Target Content | Title Keywords (select on match) |
|----------|------------------------|
| Overall vulnerability management introduction | 概述 (overview) |
| Scan mechanism / manual scan | 扫描 (scan) |
| View / repair / ignore vulnerabilities | 处理、修复 (handle, repair) |
| Repair failure causes | 失败 (failure) |
| Repair suggestions / best practices | 修复建议、实践 (repair suggestions, practices) |
| FAQ | 常见问题、FAQ (frequently asked questions) |

After locating the sub-document URL, fetch that page and extract the phrasing; when answering the user, note the source as the official help documentation.

### Level 2: Single-Page Direct Link Fallback

When Level 1 cannot locate or fetch fails, connect directly per the table below (8 key documents; URLs are the values verified when this skill was authored):

| Content | URL | Purpose |
|------|-----|------|
| Vulnerability management overview | https://help.aliyun.com/zh/security-center/user-guide/overview-4 | Feature scope, tab structure |
| Vulnerability scanning | https://help.aliyun.com/zh/security-center/user-guide/scan-for-vulnerabilities | Scan entry, scan cycle, manual scan |
| View and handle vulnerabilities | https://help.aliyun.com/zh/security-center/user-guide/view-and-handle-vulnerabilities | Repair/ignore/verify operation phrasing |
| Repair failure troubleshooting (authoritative error code page) | https://help.aliyun.com/zh/security-center/user-guide/troubleshoot-issues-that-cause-vulnerability-fixing-failures | High-frequency error code meanings and handling actions |
| Risk management FAQ | https://help.aliyun.com/zh/security-center/user-guide/faq-about-risk-management | FAQs like "fixed but still detected" |
| Install the security agent | https://help.aliyun.com/zh/security-center/user-guide/install-the-security-center-agent | Agent installation (cited when routing to the install-agent skill) |
| Vulnerability repair best practices | https://help.aliyun.com/zh/security-center/user-guide/use-cases/fix-vulnerabilities | Repair cases, basis for manual repair derivation |
| Agentless detection | https://help.aliyun.com/zh/security-center/user-guide/use-the-agentless-detection-feature | Alternative for scenarios where the Agent cannot be installed |

### Level 3: In-Site Search Fallback

When both previous levels fail, use in-site search (fetch the search results page or provide the URL for the user to browse themselves):

```
https://help.aliyun.com/search?q={keywords}
```

Search keyword combination table:

| Category | Recommended Keyword Combinations |
|------|----------------|
| Error code class | `云安全中心 漏洞修复失败 <error-code>`, `漏洞修复 <error-code> 原因` |
| Status verification class | `漏洞 已修复 仍检出`, `漏洞 重新验证`, `漏洞 扫描周期`, `漏洞 待重启` |
| Non-standard system class | `非阿里云主机 漏洞修复`, `自编译内核 漏洞`, `离线环境 补丁`, `自定义镜像 漏洞` |
| Prerequisite class | `漏洞修复 重启`, `漏洞修复 快照`, `漏洞修复 计费`, `漏洞 白名单` |

## Rule Notes

1. **URL patterns and slug stability**: official documentation URLs follow `https://help.aliyun.com/zh/security-center/{category}/{slug}` (common categories: user-guide, product-overview, developer-reference). Slugs are relatively stable, but those with numeric suffixes may increment with documentation restructurings (e.g., overview-4 → overview-5); when a direct link 404s, return to the Level 1 directory page to relocate the new slug — do not guess-change the number.
2. **Chinese/English mirrors**: the `/zh/` and `/en/` paths mirror each other; when fetching a Chinese page fails, replace `/zh/` with `/en/` to fetch the same-source English page, then paraphrase.
3. **Domain whitelist**: trust only the `help.aliyun.com` domain (API parameter details can be corroborated by the `api.aliyun.com` official debug page); third-party reposts (blogs, forums, Q&A sites) must not be used as a phrasing basis.
4. **High-frequency-update content must be verified at runtime**: error code tables, edition capability matrices, billing unit prices, OS support lists, EOL schedules, etc. — before citing, you [MUST] fetch the official page to verify the latest version; outputting from memory alone or from this skill's embedded snapshot is forbidden.
5. **Degradation order**: Level 1 anchor directory page → Level 2 single-page direct link → Level 3 in-site search; when all three levels fail, provide the user with the search URL and suggested keywords to browse themselves, honestly state that the official page could not be fetched, and never paraphrase unverified third-party content.
