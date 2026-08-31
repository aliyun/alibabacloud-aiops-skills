# Ticket Categories Reference

> Verified against the web frontend (2026-08-28 screenshots) and the qianwen
> CLI built-in category list. Two category groups behave differently.

## Group 1: Model categories — CREATE tickets

These are real ticket categories. Both CLI and API `CreateTicketNew` accept
these IDs.

| ID | Category | Keywords |
|----|----------|----------|
| `582262` | Model > Billing | usage, tokens, quota, cost, charge, bill, fee |
| `582263` | Model > Invoice | invoice, receipt, tax |
| `582264` | Model > Feature Inquiry | how to, feature, capability, tutorial, guide |
| `582265` | Model > API/SDK | API, SDK, 401, 403, 500, 429, timeout, error, call failure |
| `582266` | Model > Tool Integration | integration, connector, third-party tool |

> **Frontend parity note:** The web frontend additionally shows
> "Arena activity-related consultation" under the Model group. The CLI
> built-in list does not include it. If the user's issue is Arena-related,
> guide them to submit via the web portal.

## Group 2: App categories — REDIRECT to app site (do NOT create tickets)

The web frontend does NOT create tickets for app categories. Selecting an
app shows "For service support, please visit the app's official site".
Match this behavior: guide the user to the app's official site instead of
creating a QianWen ticket.

| ID | Category | Official site (helpUrl) |
|----|----------|------------------------|
| `miaowu` | App > MiaoWu | https://meoo.com |
| `wanxiang` | App > WanXiang | https://tongyi.aliyun.com/wan |
| `wukong` | App > WuKong | https://wukong.dingtalk.com |
| `qianwen` | App > QianWen | https://www.qianwen.com |
| `qoder` | App > Qoder | https://qoder.com |
| `qoderwork` | App > QoderWork | https://qoder.com |

**ABSOLUTE PROHIBITION:** Do not call `CreateTicketNew` with an App category
ID. Always redirect the user to the app's official site.
