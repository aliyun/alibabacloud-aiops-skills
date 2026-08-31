# Operations Guide Reference

## Ticket Description Template (create)

```
[QianWen-CLI] Concise issue summary (<=20 chars, becomes title)

[Symptom]
- What happened / When it started / Frequency

[Impact]
- Affected models/features / Business impact

[Steps tried]
- Attempted fix 1 -> result
- Attempted fix 2 -> result

[Error details]
- Error code / HTTP status / Relevant log snippet

[Diagnostics]
- qianwen doctor output (summarized)
```

## Fuzzy Rating Input Handling

When the user's reply is not a clear number, use semantic understanding and include the original input as the comment:

| User input | Interpreted rating | Comment |
|------------|-------------------|---------|
| `2` | 2 | (none) |
| `2 great` | 2 | "great" |
| `okay` / `so-so` | 1 | original text |
| `not good` / `bad` | 0 | original text |
| `very satisfied, thanks` | 2 | original text |
| `skip` | (skip rating) | — |

**Rules:**
1. If input contains a number (0/1/2), use it as the rating; remaining text becomes the comment
2. If no number, infer sentiment: positive -> 2, neutral/ambiguous -> 1, negative -> 0
3. Always use the user's original text as the comment value
4. If the user says "skip" or equivalent, skip rating entirely

## Output Display Rules

### JSON mode (recommended)

1. **Parse the JSON** and extract relevant data
2. **Present a human-readable summary** — never dump raw JSON
3. **Add analysis AFTER the summary** — separated with `---`

### NEVER

- Dump raw JSON to the user without interpretation
- Reformat or summarize text/table output
- Add prefixes like "Here's your ticket:"
- Convert text/table output to bullet points

**Correct example:**
```
Your pending tickets:

**[0005PYGCW](https://platform.qianwenai.com/home/support/detail?id=0005PYGCW)** — [QianWen-CLI] support list returns 401
**Status**: Assigned · **Created**: 2026-06-27

  ---

**Analysis**: This ticket has been assigned to an engineer...
```

## Pagination Best Practices

| Scenario | Recommended command |
|----------|---------------------|
| Check recent tickets | `list --page 1 --page-size 5` |
| Browse all active tickets | `list --page 1 --page-size 10`, then paginate |
| Find a specific ticket | Use `view <id>` directly instead of scanning the list |
| Large backlog (100+) | Start with `--page-size 10`, paginate forward only if needed |

**Rules:**
1. `--page-size` must be 1-10 (CLI hard limit); exceeding 10 returns `INVALID_ARGUMENT`
2. Incremental pagination: fetch one page at a time; do not loop through all pages automatically
3. Stop condition: if a page returns fewer records than `--page-size`, it is the last page
4. If the user asks "show all my tickets", show the first page and ask whether to see more

## Update Check

When the user asks to check for updates, **first identify the update target**:

| User intent | What to check | Command |
|---|---|---|
| "Is the CLI up to date?" | QianWen CLI binary | `qianwen version --check` |
| "Is the Support Skill up to date?" | Skills package | See below |
| Ambiguous | Ask the user to clarify | — |

**Checking Skills package version:**
1. Look for an update-check skill in sibling skill directories
2. If found, run its check script and report the result
3. If not found, inform the user the update check skill is not installed

**Important:** Any update operation must first explain the target and impact, then obtain user confirmation before executing.

## Anti-Patterns

- **Never dump raw JSON** — always parse and summarize
- **Never confuse CLI session with API key** — never offer `$DASHSCOPE_API_KEY` as a fix for CLI `AUTH_REQUIRED`
- **Never use `qianwen auth login` to fix a model API 401** — it is an API Key issue, not a CLI session issue
- **Never create a ticket without running `doctor`** first
- **Never hardcode category IDs** — always fetch via `categories`
- **Never create a ticket with an App category ID** — redirect to the app's official site instead
- **Never include plaintext credentials** in descriptions or replies — always mask
- **Never skip auto-diagnosis** — many issues are resolvable without a ticket
- **Never fabricate ticket IDs or statuses** — always query from CLI/API
- **Never skip rating invitation** after closing a ticket
- **Never reply to or close a terminal-status ticket** — offer to create a new ticket instead
- **Never upload any attachments** — decline and direct to the web portal
- **Never modify customer service replies** — relay verbatim
- **Never perform authorization on behalf of the user** — must be done on the web portal
- **Never ignore screenshots in replies** — notify and guide to the web portal
- **Never attempt batch operations** — one ticket at a time

## FAQ / Troubleshooting

| Question | Answer |
|----------|--------|
| Forgot ticket ID? | Run `list --page-size 5` to see recent tickets |
| CLI returns 401 but `auth status` shows authenticated? | Token may have silently expired; run `qianwen auth login` |
| `create` succeeded but no ticket ID returned? | Check network; run `list --page-size 5` to find the recent ticket |
| Need to upload screenshots/attachments? | CLI cannot upload; use the web portal ticket page |
| Accidentally closed a ticket? | Closed tickets cannot be reopened; create a new ticket referencing the old ID |
| `auth login --complete` never returns? | Wait 30s then interrupt; use the web portal instead |
| How to check CLI version? | `qianwen version` (needs >= 1.2.0); upgrade: `qianwen update` |
| How to skip rating after closing? | Reply "skip" when prompted to rate |
