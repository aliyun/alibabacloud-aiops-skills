# Troubleshooting

For CLI, authentication, permission, region or connection issues, see
[common troubleshooting](../troubleshooting.md).

## Index operations

| Symptom | What to check | Details |
| --- | --- | --- |
| `IndexConfigNotExist` | An absent index, distinct from a missing Logstore. Creating one is a separate configuration change. | [Index inspection](manage-index-config.md#read-an-index) |
| `IndexAlreadyExist` | Current configuration before preparing an update. | [Read the index](manage-index-config.md#read-an-index) |
| `LogStoreNotExist` | Logstore name, owning Project, and service location. | [Region and endpoint configuration](../regions.md) |
| Command parameters or request construction fail | The target and JSON input shape. | [Index operations](manage-index-config.md#changes) |
| `IndexInfoInvalid`, `ParameterInvalid` or configuration rejected | Reported field, type, value and applicable setting. | [Index parameters](index-configuration.md#top-level-parameters) |
| A bundled script cannot run | Python runtime and the absolute script/input paths. | [Index validator](entry.md#index-validator) |

An index read against the requested target can help distinguish access failures
from an absent configuration.
