# Compatibility Baseline

Execution baseline validated on 2026-09-23 with:

- Aliyun CLI `3.5.0`
- official `ecd` plugin `0.9.4`
- official `appstream-center` plugin `0.9.6`
- both plugins use type `meta` and metadata format `protobuf`
- minimum CLI version declared by both plugins: `3.5.0`

The environment check also compares installed plugins with the official stable remote index. On 2026-09-24, it reported `ecd` `0.9.4` installed with `0.9.6` available, and `appstream-center` `0.9.6` installed with `0.9.7` available. Update detection is advisory and never changes local plugins without user authorization.

The configured official WUYING product scope is stored in `products.json`:

- `ecd` / `aliyun-cli-ecd`
- `appstream-center` / `aliyun-cli-appstream-center`
- `eds-user` / `aliyun-cli-eds-user`
- `wyota` / `aliyun-cli-wyota`
- `wss` / `aliyun-cli-wss`

The generated catalog records every command and supported API version reported by each installed configured plugin rather than maintaining a hand-written Action list. A partial catalog explicitly records configured products whose plugins are not installed.

ECD read validation succeeded for `describe-regions` and `describe-desktops`. A `start-desktops` request was validated only with `--cli-dry-run`; no mutation was sent.

For App Stream, live plugin help was validated for `list-browser-instance-group` and `list-authorized-users` with API version `2021-09-01`. The authorization-user workflow was confirmed to return the expected users for a cloud browser group.

`eds-user`, `wyota`, and `wss` are included in the product configuration but were not installed in the validation environment on 2026-09-23. Their commands must not be claimed as locally generated or execution-validated until the official plugins are installed and the catalog is regenerated.

The end-to-end execution validation was performed on macOS arm64. Other operating-system packages are distributed by Aliyun CLI, but they are not claimed as end-to-end validated by this artifact.
