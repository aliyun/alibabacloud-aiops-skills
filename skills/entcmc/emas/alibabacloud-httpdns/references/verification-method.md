# Verification Method

## Static verification

1. `SKILL.md` exists at repository root.
2. `related_apis.yaml` exists and lists every used API.
3. `SKILL.md` has the 11 required sections in order.
4. `SKILL.md` is under 500 lines.
5. Permission failure handling block is present verbatim.
6. No credential file content, AK, SK, token, or password is committed.

## CLI availability verification

Use an empty temporary HOME if the local user profile is malformed and only
help output is needed:

```bash
HOME=/private/tmp/aliyun-empty-home aliyun version
HOME=/private/tmp/aliyun-empty-home aliyun httpdns --help
HOME=/private/tmp/aliyun-empty-home aliyun httpdns get-resolve-statistics --help
```

Expected:

- `aliyun version` is `>= 3.3.3`.
- `aliyun httpdns --help` lists product `Httpdns`, version `2016-02-01`.
- The required API appears in the available API list.

## Runtime verification

Account lookup:

- Response has `RequestId`.
- Account fields are present.
- Secret-like fields are masked in the final answer unless raw output was explicitly requested.

Domain add/delete:

- Command returns `RequestId`.
- After `add-domain`, run `list-domains`, preferably with `--search <domain>`, and confirm the target domain appears.
- If `add-domain` returns `DomainAlreadyExists` for a generated `example.com` placeholder domain, first confirm presence with `list-domains`, then run `delete-domain`, rerun `add-domain`, and finish with `list-domains` verification. Do not use this replacement flow for real user domains without explicit approval.
- For placeholder/evaluation delete workflows, if `list-domains --search <domain>` shows the target is absent before deletion, create the precondition with `add-domain --domain-name <domain>` before calling `delete-domain`.
- After `delete-domain`, run `list-domains` or `describe-domains` and confirm the target domain is absent.
- If `add-domain` fails, still run `list-domains` when possible and report both the mutation error and whether the domain already exists.

Domain list:

- Response has page fields or domain collection fields.
- Pagination values match requested `--page-number` and `--page-size` when present.

Usage pull:

- Response has `RequestId`.
- Result corresponds to requested `--domain-name`, `--granularity`, and `--time-span`.
- If no data is returned, state that the API call succeeded but no records matched.

## Error handling

- Permission errors: follow the mandatory RAM workflow in `SKILL.md`.
- `UserDisabled`: report an account/service restriction such as debt, inactive HTTPDNS service, or risk control; this is not a RAM permission failure unless the response explicitly says permission denied.
- `product not exists` or `action not found`: run `aliyun plugin update`, then re-check `aliyun httpdns --help`.
- Parameter errors: check that the command uses plugin-mode action names and flags, required parameters, and JSON formatting where needed.
- Credential errors: ask the user to fix the active profile; do not inspect credential files.
