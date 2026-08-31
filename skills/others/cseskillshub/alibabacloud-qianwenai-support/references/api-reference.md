# QianWen Support API Reference

> This file documents the QianWen platform HTTP API used by the API backend.
> The CLI backend wraps `qianwen support` commands instead.
> All action names and parameter names below are verified by real API calls.

## Endpoint

```
POST https://cli.qianwenai.com/data/v2/api.json
Content-Type: application/json
Authorization: Bearer <token>
```

## Request Body

```json
{
  "product": "Workorder",
  "action": "<Action>",
  "region": "cn-beijing",
  "params": { ... }
}
```

## Response Envelope

```json
{
  "requestId": "...",
  "code": "200",
  "message": null,
  "data": { "Code": 0, "Success": true, "Data": { ... } }
}
```

## Actions (verified)

| Action | Purpose | Key params |
|--------|---------|-----------|
| `ListTickets` | List tickets | `Page`, `PageSize`, `IndependentSiteTag`, `Params` (JSON string) |
| `GetTicket` | View ticket detail | `TicketId`, `Region`, `IndependentSiteTag` |
| `ListEnhancedMessage` | View ticket messages | `TicketId`, `PageLimit` |
| `CreateTicketNew` | Create ticket | `CategoryId`, `Description`, `AcceptLanguage`, `IndependentSiteTag` |
| `CreateMessage` | Reply to ticket | `TicketId`, `Content` |
| `CancelTicket` | Close/cancel ticket | `TicketId` |
| `SubmitCard` | Rate ticket | `PostParam` (JSON string: `ticketId`, `satisfaction`, `suggest`) |
| `GetCategoryTreeByProductCodes` | Get categories | `ProductCodes` (JSON string `["bailian"]`) |
| `SuggestCategoryNew` | Suggest category | `Content`, `Channel` |

## Authentication

Token is obtained via `qianwen auth login` (browser device flow).
Stored in macOS keychain (`qianwen-cli` / `cli_credentials`).
Can also be provided via environment variable `QIANWEN_ACCESS_TOKEN`.

## Error Codes

| Code | Meaning |
|------|---------|
| `200` + `Success: true` | Operation succeeded |
| `2011` | No permission to view this ticket (wrong account or ticket not found) |
| `MissingTicketId` | Missing required `TicketId` parameter |
| `MissingRegion` | Missing required `Region` parameter |
| `InvalidAction.NotFound` | Action name does not exist |
