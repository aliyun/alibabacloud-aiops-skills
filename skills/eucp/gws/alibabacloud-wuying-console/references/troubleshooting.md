# Troubleshooting

## CLI is missing or outdated

Aliyun CLI 3.5.0 or later is required. Use the scoped automatic workflow in
[setup.md](setup.md), unless the user explicitly prohibited installation/upgrade.
Do not pause for a separate CLI/plugin installation authorization message.
On macOS with Homebrew already available, install the official CLI with:

```bash
brew install aliyun-cli
```

Upgrade an independent installation with:

```bash
aliyun upgrade --yes
```

For a Homebrew-managed installation, use `brew upgrade aliyun-cli` instead.
When Homebrew/GitHub cannot be reached, follow the official CDN script/archive
fallbacks in `setup.md`; do not change mirrors, TLS checks or credentials.
Then rerun `python3 scripts/check_environment.py` to verify the effective binary
and version before continuing.

## Plugin is missing

Run `python3 scripts/check_environment.py --required-products <task-products...>`.
It checks every configured product but plans repairs only for the requested scope.
Automatically install missing required plugins in one batch, for example:

```bash
aliyun plugin install --names ecd appstream-center eds-user wyota wss
```

The five-product example is for full setup only; ordinary tasks install only
their required subset. Check-only/no-install restrictions still take precedence.
If at least one configured product is ready, the environment check returns
`partial` rather than blocking every product. Continue business execution only
for `ready_products` with valid OAuth. Regenerate and search the workflow catalog
after dependency changes, then resume the original task.

## Plugin update status is unavailable

The default environment check runs `aliyun plugin list-remote` and compares each installed plugin with the official latest stable version. A temporary remote-index or network failure does not block compatible installed plugins. Retry later, or use `--skip-update-check` only when intentionally working offline.

When `updates_available` contains a compatible product, report the installed and
latest versions as advisory and continue the task. Do not ask whether to upgrade
or wait for a reply. Optional upgrades run only when explicitly requested;
missing/incompatible task-required dependencies and officially verified required
command gaps follow automatic repair in `setup.md`, without another installation
authorization question:

```bash
aliyun plugin update --name <plugin-package>
```

Regenerate the command catalog after an update because commands, parameters, descriptions, or supported API versions may have changed.

## Command is reported as unknown

Always pass the API version explicitly. A product plugin's default version can expose a different command set from the version that contains the required operation.

Check the live product catalog:

```bash
aliyun <product> --api-version <version> --help-all
```

Then inspect the exact command:

```bash
aliyun <product> <command> --api-version <version> --help
```

If the expected product is absent from the generated catalog, inspect `missing_products`, check `products.json`, verify that its official plugin is installed, and regenerate with `python3 scripts/generate_command_catalog.py`.

## Required parameter is unclear

- Use the live command help, not a remembered console form.
- Query authoritative resources to resolve IDs and regions.
- Ask the user only for information that cannot be queried or safely inferred.
- Do not reinterpret `RegionId` as another similarly named field.

## Output query returns nothing

Do not assume the example query path in help matches every runtime response. First inspect the unfiltered JSON response. For example, response containers may be arrays even when an older help example shows a nested singular property.

Do not use `--output json`. In Aliyun CLI 3.5.0, `--output` expects table configuration such as `cols=...`; API responses are JSON by default. Use `--cli-output json` only to make local CLI help and error output machine-readable.

## API request fails

- Preserve the exact error code, message, HTTP status, and `RequestId`.
- Redact credentials and authorization data.
- For read requests, retry only transient failures with bounded attempts.
- For mutations, query the target state before retrying to avoid duplicate effects.
- Report whether the failure occurred during local argument validation, authentication, gateway/API execution, or post-operation verification.

## Profile is invalid or expired

Use the standard Aliyun CLI profile store and follow [authentication.md](authentication.md). Do not copy profile files into a temporary custom location as a workaround for plugin behavior.

If `local_check_errors` reports an inspection failure, retry the failed local
probe once first. Unknown state is neither proof of missing software nor proof
of expired OAuth; do not reinstall or initiate login from that failure alone.
