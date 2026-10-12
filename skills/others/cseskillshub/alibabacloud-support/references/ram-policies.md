# RAM Policies

This document records what was measured on 2026-10-10 with the evaluation role and the
official Alibaba Cloud system policy, not an assumed permission model. The skill writes
tickets, so it is deliberately not a query-only skill.

## Operations that this client calls

| Workorder operation | Plugin-mode CLI command | Direction |
|---|---|---|
| ListProducts | `aliyun workorder list-products` | catalog read |
| ListCategories | `aliyun workorder list-categories` | catalog read |
| ListTickets | `aliyun workorder list-tickets` | ticket read, also used by create reconciliation |
| GetTicket | `aliyun workorder get-ticket` | ticket read, state re-check before every write |
| ListTicketNotes | `aliyun workorder list-ticket-notes` | conversation read |
| CreateTicket | `aliyun workorder create-ticket` | write |
| ReplyTicket | `aliyun workorder reply-ticket` | write |
| EvaluateTicket | `aliyun workorder evaluate-ticket` | write |
| CloseTicket | `aliyun workorder close-ticket` | write |

All nine are resolved through the aliyun CLI workorder product plugin, API version
2021-06-10, endpoint `workorder.aliyuncs.com`, and every request is sent as `POST`
(confirmed locally with `--cli-dry-run`, which prints the request without sending it).

## Measured authorization behaviour

- Assumed role: `acs:ram::1552974654746705:role/skillsclienttest`, evaluated through
  `sts:AssumeRole` with a temporary session, the same credential path as online evaluation.
- Attached policies on that role at measurement time: the system policy `ReadOnlyAccess`
  (default version `v20`) plus five custom skill policies. The `ReadOnlyAccess` document
  contains no statement for the ticket namespaces, yet `ListProducts`, `ListTickets`,
  `GetTicket` and `ListTicketNotes` all succeeded.
- Conclusion: Workorder ticket queries are authorized against the identity that owns the
  ticket, so a product-specific read grant was not required in that account. A query that
  returns nothing only proves that the current credential owner has no matching ticket; it
  never proves that the account has no ticket at all.
- The four write operations were intentionally not executed against the live service during
  the audit, because a write cannot be undone cleanly. `doctor` therefore reports
  `permissionVerified: false` for every remote capability, and an unauthorized write surfaces
  as a normal API rejection instead of a pre-flight verdict.

## Official grant for ticket management

`AliyunSupportFullAccess` is the system policy for the ticket system. It was read through
`ram GetPolicy` on 2026-10-10: default version `v3`, update date 2025-12-18, description
"the permission to manage the ticket system", with full access to three namespaces: `support`,
`smartservice` and `customersentiment`. Attach this system policy when the customer or the
sub-account has to create, reply, evaluate or close tickets; the skill does not need any other
product permission.

## Least-privilege custom policy (draft, names not verifiable locally)

Alibaba Cloud does not publish a granular action list for the ticket namespaces, and the
system policy above only ships namespace-level grants. The following draft mirrors the nine
operations this client actually calls and is offered for accounts that insist on an
explicit action list. Validate it with one throw-away RAM user before enforcing it, and fall
back to `AliyunSupportFullAccess` when a name is rejected:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "support:ListProducts",
        "support:ListCategories",
        "support:ListTickets",
        "support:GetTicket",
        "support:ListTicketNotes",
        "support:CreateTicket",
        "support:ReplyTicket",
        "support:EvaluateTicket",
        "support:CloseTicket"
      ],
      "Resource": "*"
    }
  ]
}
```

No wildcard action is declared, and no permission outside the ticket namespaces is required.
The client never calls `sts:AssumeRole` itself; it only consumes whatever identity the aliyun
CLI default credential chain resolves.

## Action to code mapping

| Action group | Where it is called | Failure handling |
|---|---|---|
| Catalog reads | `command_catalog` | deterministic rejection, ticket creation stops |
| Ticket and note reads | `command_ticket`, `current_ticket_state`, `non_terminal_state` | deterministic rejection; a missing state blocks writes |
| Reconciliation reads | `reconcile_create` after an indeterminate `CreateTicket` | read-only, never re-issues the write |
| Writes | `command_ticket` behind `require_confirmation` | indeterminate results stop with an explicit no-retry instruction |
