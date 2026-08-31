# Category Selection Strategy

> How to choose a ticket category and keep the listing fresh.

## Selection Strategy

1. Match the user's issue to a group:
   - Model/API/billing/invoice/feature questions -> Group 1 (create ticket)
   - App-specific issues (MiaoWu/WanXiang/WuKong/Qoder/QoderWork) -> Group 2 (redirect)
2. For Group 1: API/SDK failures -> `582265`; billing/quota -> `582262`;
   invoice -> `582263`; usage/how-to -> `582264`; integration -> `582266`
3. For Group 2: provide the helpUrl and stop; no ticket creation
4. NEVER fabricate category IDs not provided by the `categories` command

## Runtime refresh

```bash
python3 scripts/qianwen_support.py categories          # CLI backend (dynamic)
python3 scripts/qianwen_support.py --backend api categories   # API backend (builtin)
```

The `categories` output includes a `type` field (`ticket` or `redirect`) and
`helpUrl` for redirect categories.
