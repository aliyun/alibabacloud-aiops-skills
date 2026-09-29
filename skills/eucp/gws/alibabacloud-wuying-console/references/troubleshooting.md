# Troubleshooting

## CLI is missing or outdated

Aliyun CLI 3.5.0 or later is required. Request user authorization before
installing or upgrading local software. On macOS, install the official CLI with:

```bash
brew install aliyun-cli
```

Upgrade an existing installation with:

```bash
aliyun upgrade
```

Then rerun `python3 scripts/check_environment.py` to verify the installed
version before continuing.

## Plugin is missing

Run `python3 scripts/check_environment.py`. It checks every product listed in `products.json`. Follow its installation guidance only after the user authorizes local software changes. For example:

```bash
aliyun plugin install --name aliyun-cli-ecd
aliyun plugin install --name aliyun-cli-appstream-center
aliyun plugin install --name aliyun-cli-eds-user
aliyun plugin install --name aliyun-cli-wyota
aliyun plugin install --name aliyun-cli-wss
```

If at least one configured product is ready, the environment check returns `partial` rather than blocking every product. Continue only for products listed in `ready_products`.

## Plugin update status is unavailable

The default environment check runs `aliyun plugin list-remote` and compares each installed plugin with the official latest stable version. A temporary remote-index or network failure does not block compatible installed plugins. Retry later, or use `--skip-update-check` only when intentionally working offline.

When `updates_available` contains a product, report the installed and latest versions. Update only after user authorization:

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
