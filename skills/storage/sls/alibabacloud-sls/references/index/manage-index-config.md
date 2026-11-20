# Index operations

## Read an index

| Target | Command | Result |
| --- | --- | --- |
| Logstore | `aliyun sls index get` | Current index configuration. |
| Logstore-type StoreView | `aliyun sls store-view get-index` | Index configurations of its source Logstores. |

StoreView responses contain `indexes[]`, with a source `project`, `logstore` and `index`
in each entry; source settings may differ. See [StoreView permissions](ram-policies.md#storeview-inspection).
The [query behavior](index-configuration.md#query-behavior) sections explain the returned settings.

## Changes

| Command | Purpose |
| --- | --- |
| `aliyun sls index create` | Create a Logstore index. |
| `aliyun sls index update` | Update an existing Logstore index. |
| `aliyun sls index delete` | Remove a Logstore's index configuration. |

`index update` replaces the complete configuration. Prefer comparing a diff against
the current settings from `index get` to spot unintended removals or changes.
Both `--from-file` and individual flags supply the replacement configuration.

For writable fields and service-maintained discovery entries, see
[index parameters](index-configuration.md#top-level-parameters) and
[automatic discovery](index-configuration.md#automatic-index-discovery).
For propagation and the effect on existing logs, see
[configuration changes and historical data](index-configuration.md#configuration-changes-and-historical-data).

For lookup, configuration and command errors, see [index troubleshooting](troubleshooting.md).
