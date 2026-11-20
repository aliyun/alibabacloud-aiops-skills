# SLS insights

SLS provides managed built-in Stores containing runtime logs, audit logs,
access logs and alert-trigger history for its service features. These cover
consumer-group lag, data-transformation and Scheduled SQL task execution,
Project access, LoongCollector runtime status and collection-configuration
diagnostics.

## Context references

[Service logs](service-logs.md) introduces collection categories,
activation and storage configuration. The references below describe each
built-in Store and its data; names are managed defaults, not fixed destinations.

| Store | Project | Context | Charged? | Activation | Reference |
| --- | --- | --- | --- | --- | --- |
| `internal-diagnostic_log` | Same Project or the Project specified in service-log configuration | Consumer-group lag logs; Logtail/LoongCollector alarm and collection logs; Scheduled SQL runtime logs; transformation/import/delivery runtime logs | No | [Enable service logs](service-logs.md#enable-change-or-disable) | [Topic references](diagnostic-logs/entry.md) |
| `internal-operation_log` | Same Project or the Project specified in service-log configuration | Project access logs | Yes, ordinary Logstore billing | [Enable detailed service logs](service-logs.md#enable-change-or-disable) | [Project access logs](operation-log.md) |
| `internal-etl-log` | Current Project | Transformation preview output and legacy task diagnostics | No | [Automatic when using transformation preview/tasks](etl-logs.md#when-to-use-it) | [ETL logs](etl-logs.md) |
| `internal-alert-history` | Current Project | Rule executions, including non-firing evaluations | No | [First console visit to rule details](alert-history.md#project-execution-history) | [Project execution history](alert-history.md#project-execution-history) |
| `internal-alert-center-log` | `sls-alert-<primary-account-id>-<center-region>` | Alert lifecycle across all Projects and regions in the account | No | [First console setup of alerting](alert-history.md#global-alert-center-history) | [Global alert center history](alert-history.md#global-alert-center-history) |

Free use covers managed ingestion, storage and query/analysis. Optional
processing/export operations and SMS/voice notifications have separate charges.

## Safety rules for managed built-in stores

Do not directly modify these Stores' configuration or indexes, or delete the
Stores or their indexes. Their owning SLS feature modules manage them
automatically; direct changes can disrupt those modules' operation.

## Related capabilities

- [Query and analysis](../query/entry.md): query syntax and execution.
- [Log collection](../loongcollector/entry.md): collector management and troubleshooting.
- [Alert event diagnosis](../alerting/diagnosis/diagnose.md): trigger and root-cause investigation.
