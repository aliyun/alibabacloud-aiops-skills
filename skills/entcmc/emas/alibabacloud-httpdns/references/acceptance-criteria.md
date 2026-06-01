# Acceptance Criteria

## Product and action names

Correct:

```bash
aliyun httpdns get-account-info
scripts/httpdns-openapi.sh add-domain --domain eval-add-a1b2c3d4.example.com --yes
aliyun httpdns get-resolve-statistics --domain-name eval-stats-a1b2c3d4.example.com --granularity day --time-span 7
```

Incorrect:

```bash
aliyun Httpdns get-account-info
aliyun httpdns get-resolve-statistics --domain-name eval-stats-a1b2c3d4.example.com
```

Reason: this product exposes `httpdns` as the CLI product and requires
plugin-mode kebab-case action names.

## Domain operations

Correct:

```bash
scripts/httpdns-openapi.sh add-domain --domain eval-add-a1b2c3d4.example.com --yes
aliyun httpdns list-domains --search eval-add-a1b2c3d4.example.com --page-number 1 --page-size 100
scripts/httpdns-openapi.sh delete-domain --domain eval-add-a1b2c3d4.example.com --yes
```

For an add-and-confirm request, `add-domain` must be followed by `list-domains`.
Use `--search <domain>` when available so the verification response is scoped to
the target domain.

Idempotent placeholder/evaluation case:

```bash
scripts/httpdns-openapi.sh add-domain --domain eval-add-a1b2c3d4.example.com --yes
# If the response is DomainAlreadyExists:
aliyun httpdns list-domains --search eval-add-a1b2c3d4.example.com --page-number 1 --page-size 100
scripts/httpdns-openapi.sh delete-domain --domain eval-add-a1b2c3d4.example.com --yes
scripts/httpdns-openapi.sh add-domain --domain eval-add-a1b2c3d4.example.com --yes
aliyun httpdns list-domains --search eval-add-a1b2c3d4.example.com --page-number 1 --page-size 100
```

This delete-and-readd flow is only acceptable for placeholder/evaluation domains
such as generated domains under `example.com`, or after explicit user
approval. For real user domains, `DomainAlreadyExists` should be treated as an
idempotent end-state success without deleting the existing domain.

Incorrect:

- Using `add-domain` with `--domain` instead of plugin-mode `--domain-name`.
- Using `describe-domains --search`; `describe-domains` does not accept `--search`.
- Running `delete-domain` without a target domain.

Reason: `--domain-name` is required and uses plugin-mode spelling.
`describe-domains` does not accept `--search`, and add-and-confirm workflows
must verify with `list-domains` so the domain list check is explicit.

Incomplete add-and-confirm sequence:

```bash
scripts/httpdns-openapi.sh add-domain --domain eval-add-a1b2c3d4.example.com --yes
aliyun httpdns describe-domains --page-number 1 --page-size 20
```

Reason: the add call is valid, but this sequence misses the required
`list-domains` verification.

Delete validation precondition:

```bash
aliyun httpdns list-domains --search eval-delete-a1b2c3d4.example.com --page-number 1 --page-size 100
# If absent and this is a placeholder/evaluation delete workflow:
scripts/httpdns-openapi.sh add-domain --domain eval-delete-a1b2c3d4.example.com --yes
scripts/httpdns-openapi.sh delete-domain --domain eval-delete-a1b2c3d4.example.com --yes
aliyun httpdns list-domains --search eval-delete-a1b2c3d4.example.com --page-number 1 --page-size 100
```

Reason: delete API assertions require an actual delete path. It is acceptable to
create and remove placeholder/evaluation domains under `example.com`; do not
create real user domains just to make `delete-domain` succeed unless the user
explicitly asked to validate the delete API path.

## Refresh cache

Correct:

```bash
scripts/httpdns-openapi.sh refresh-cache --domains eval-refresh-a1b2c3d4.example.com --yes
```

Incorrect:

- Passing `--domains` as a JSON array string.
- Using `--domain-name` with `refresh-resolve-cache`.

Reason: plugin-mode `refresh-resolve-cache` expects `--domains` as space-separated list values, not a JSON array string. If the service returns `REFRESH_DOMAINS_LIMIT`, report the RequestId and continue with the requested list/verification step; this is an account-level quota response, not a CLI syntax issue.

## Usage statistics

Correct:

```bash
aliyun httpdns get-resolve-statistics --domain-name eval-stats-a1b2c3d4.example.com --granularity day --time-span 7
aliyun httpdns get-resolve-count-summary --granularity day --time-span 7
```

Incorrect:

```bash
aliyun httpdns get-resolve-statistics --domain-name eval-stats-a1b2c3d4.example.com --time-span 7
aliyun httpdns get-resolve-count-summary --granularity day
```

Reason: statistics APIs require both `--granularity` and `--time-span`;
domain-level statistics also requires `--domain-name`.

## Sensitive output

Correct behavior:

- Call `get-account-info` directly when the user asks for account/key information, then return masked values by default.
- Mask secret-like values in command output and summaries, for example `abcd****wxyz`.
- `scripts/httpdns-openapi.sh account-info` masks secret-like JSON fields by default.
- Include `RequestId` when present.

Incorrect behavior:

- Asking a follow-up confirmation only to return masked account/key information.
- Reading `~/.aliyun/config.json`.
- Printing `AccessKeySecret`, `AccountSecret`, tokens, or passwords without explicit user request.
- Using `scripts/httpdns-openapi.sh account-info --raw` unless the user explicitly asks for unmasked/raw/full secret values.
- Persisting secrets into repository files, evals, logs, or references.
