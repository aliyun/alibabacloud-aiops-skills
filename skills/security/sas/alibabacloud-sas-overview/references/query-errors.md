# Query failures and bounded retries

Before API examples, initialize and reuse the manifest-derived `USER_AGENT` as
described in [SKILL.md](../SKILL.md#observability).

For read queries only, retry a transient network failure (bad file descriptor,
connection reset, timeout), service-unavailable/internal-error response or throttling
at most twice after the first attempt. Wait 1 second, then 2 seconds. Each attempt
has a 60-second timeout. Keep the same confirmed arguments, profile and session UA.
Retry the failed page, not already collected pages; deduplicate and validate totals.

Use the allowlisted wrapper for overview CLI queries after parameter confirmation:

```bash
python3 scripts/cli_query.py -- aliyun sas describe-version-config --user-agent "$USER_AGENT"
```

`host_inventory.py` uses this wrapper internally. Other workflow/verification
commands show the underlying CLI call; execute them through this wrapper for the
same retry policy. It accepts only the read commands listed by this Skill. It does
not retry writes, install actions or arbitrary shell commands.

Permission/authentication failures, invalid/missing parameters, wrong endpoints,
unsupported versions and service-not-opened errors require diagnosis, not repeated
calls. A valid HTTP/CLI success with null business fields is a validation failure,
not a reason to retry indefinitely. Unknown errors stop immediately. The wrapper
returns structured-response validation errors without retrying them.

After exhaustion, report the affected item, region/page, attempts, safe error code
and RequestId when provided. Do not print credentials or raw CLI debug output.
Keep independent successful items, label coverage partial, and offer a later retry;
do not fabricate zero, full completion, or an edition/purchase recommendation.
