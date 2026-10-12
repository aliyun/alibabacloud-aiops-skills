# Workorder API Reference

Every entry below was verified on 2026-10-10 against the aliyun CLI 3.4.5 workorder product
plugin (`aliyun-cli-workorder` 0.9.0), API version 2021-06-10, endpoint
`workorder.aliyuncs.com`. Read operations were executed with temporary STS credentials; write
operations were verified with `--cli-dry-run`, which prints the constructed request without
sending it.

## Transport

The plugin builds every Workorder request as `POST` with `Style: RPC`. Simple scalar
parameters go into the query string, and content-bearing parameters go into the request body,
as proven by the dry-run output:

| Command | Request line in dry-run |
|---|---|
| `list-products` | query `Name`, `Language` |
| `list-categories` | query `Language`, body `{"Name": ..., "ProductId": ...}` |
| `list-tickets` | query `PageNumber`, `PageSize`, body `{"StartDate", "EndDate", "Keyword", "TicketId"}` |
| `get-ticket` | body `{"TicketId": ...}` |
| `create-ticket` | body `{"CategoryId", "Description", "Severity", "Title"}` |
| `reply-ticket` | body `{"Content", "Encrypt", "TicketId"}` |
| `evaluate-ticket` | body `{"Content", "Score", "Solved", "TicketId"}` |
| `close-ticket` | body `{"TicketId": ...}` |

The client adds `--retry-count 0`, `--connect-timeout 10`, `--read-timeout <per call>` and the
tracing `--user-agent`, and runs the process without a shell.

## Operations and parameters

| Plugin command | API operation | Parameters (CLI flag → API name) |
|---|---|---|
| `list-products` | ListProducts | `--name` → Name (fuzzy), `--biz-language` → Language (`zh`, `en`, `jp`) |
| `list-categories` | ListCategories | `--product-id` → ProductId (required, int), `--name` → Name, `--biz-language` → Language |
| `list-tickets` | ListTickets | `--page-number` → PageNumber (required), `--page-size` → PageSize (required), `--start-date` → StartDate (epoch ms), `--end-date` → EndDate (epoch ms), `--keyword` → Keyword, `--ticket-id` → TicketId, `--status-list` → StatusList, `--ticket-id-list` → TicketIdList, `--uid` → UID |
| `get-ticket` | GetTicket | `--ticket-id` → TicketId (required), `--uid` → UID |
| `list-ticket-notes` | ListTicketNotes | `--ticket-id` → TicketId (required), `--uid` → UID |
| `create-ticket` | CreateTicket | `--category-id` → CategoryId (required, string), `--description` → Description (required, plain text), `--severity` → Severity (required, `1` normal or `2` urgent), `--title` → Title, `--email` → Email, `--file-name-list` → FileNameList, `--secret-info` → SecretInfo. `--creator-id` exists for MPK reseller accounts and is never set by this client |
| `reply-ticket` | ReplyTicket | `--ticket-id` → TicketId (required), `--content` → Content (required), `--encrypt` → Encrypt (required bool, always `false` here), `--file-name-list`, `--uid` |
| `evaluate-ticket` | EvaluateTicket | `--ticket-id` → TicketId (required), `--score` → Score (required, `1`-`5`), `--solved` → Solved (required bool), `--content` → Content, `--uid` |
| `close-ticket` | CloseTicket | `--ticket-id` → TicketId (required), `--uid` → UID |

`ListTicketNotes` is the documented way to read back a reply, and `GetAttachmentUploadUrl`
exists for attachments; this skill deliberately does not use attachments.

## Response envelope

Measured shapes, all at the top level of the JSON body:

```json
{
  "Code": 0,
  "Success": true,
  "RequestId": "01A12435-...",
  "Data": []
}
```

- `Code` accepts both `0` and `200` as success. A failure is `{"Code": 300, "Message": "...",
  "Success": false}`; the client keeps `Code`, a redacted `Message` and `RequestId` for
  diagnostics and stops on `Success: false`.
- `ListProducts` returns `Data` as a list of directories, each with `DirectoryId`,
  `DirectoryName` and `ProductList[]` of `{ProductId, ProductName}`.
- `ListTickets` returns `Data[]` of `{TicketId, Title, Status{Label, Value}}` plus
  `PageNumber`, `PageSize` and `TotalCount`. Reconciliation requires
  `TotalCount == len(Data)`, otherwise the page is treated as incomplete.
- `GetTicket` returns `Data` as `{TicketId, Title, Description, CategoryId, Severity,
  CreateTime (epoch ms), CreatorId, Status{Label, Value}}`. Measured terminal example:
  `Status: {"Label": "...", "Value": "6"}`.
- `ListTicketNotes` returns `Data[]` of `{DialogId, CreateTime, Type, Status,
  Dialog{Content}, Attachments[], User{UserId}}`.
- `CreateTicket` returns the new ticket number in `Data`; the client also accepts a
  `Data.TicketId`, a top-level `TicketId` or `Data.Id`, and treats an unresolvable ticket
  number as an indeterminate result rather than a success.
- The write probes returned `Data: true` for Reply, Evaluate and Close under mock transport,
  so the client surfaces the raw `apiResponse` instead of depending on a payload shape.

## Status values

`Status.Value` is the stable field and `Status.Label` is localized text. The client treats
`6`, `closed`, `resolved` and `confirmed`, plus the Chinese localized labels for closed,
awaiting-rating and completed, as terminal, and re-reads the status immediately before
replying, closing or evaluating.
