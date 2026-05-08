# Introduction

Channel configuration (Settings) is used to control channel-level parameters such as transfer rate, concurrency, and error handling strategy for data synchronization tasks, affecting the performance and reliability of the entire data synchronization process.

**Core Features:**
- Control job transfer rate and error record count
- Configure task concurrency and distributed execution mode
- Set dirty data handling strategy
- Configure JVM parameters and memory usage
- Set time zone


## Parameter Description

| Parameter Name | Parameter Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| jvmOption | JVM parameters. Configurable properties for synchronization task runtime memory, etc. For example, `-Xms1024m -Xmx1024m` indicates a runtime memory of 1024MB. When not specified, the system determines it automatically. | N | Auto-filled by system | Y | |
| speed.concurrent | Desired maximum task concurrency. Due to resource constraints or task characteristics, the actual concurrency may be less than or equal to this value. Billing is based on the actual executed concurrency. | Y | 3 | Y | Frontend default: 3; Value range: 1-32; Linkage logic: display over-limit warning when exceeding the resource group's maximum supported concurrency and >= 8; display special warning for MongoDB data source with concurrency >= 2 |
| executeMode | Execution mode. When enabled, task slices are distributed across multiple execution nodes for concurrent execution, utilizing fragmented resources. When disabled, the configured concurrency is single-machine process concurrency. | N | null (disabled) | Y | Frontend default: null (disabled); Prerequisite: concurrency >= 8 to enable; Frontend options: `Enable Distributed Execution` → `distribute`, `Disable (Single-Machine Mode)` → `null`; Linkage logic: requires secondary confirmation when enabling, and displays a prompt message |
| speed.throttle | Whether to throttle. Throttling protects the data source from read/write pressure; without throttling, maximum transfer performance under current hardware conditions is provided. | N | false (no throttling) | Y | Frontend default: false (no throttling); Frontend options: `Throttle` → `true`, `No Throttling` → `false`; Linkage logic: display speed.mbps field when throttling is selected |
| speed.mbps | Throttling limit, in MB/s. | Required when throttling | None | Y | Display condition: when speed.throttle is true (throttling selected); Validation rule: must be a positive integer |
| errorLimit.strategy | Dirty data strategy. Dirty data refers to source data that does not conform to the destination data source's required format and cannot be written (e.g., type mismatch, NULL values not supported, etc.). | Y | ZeroTolerance | Y | Frontend default: ZeroTolerance; Frontend options: `Ignore` → `Ignore`, `Tolerate Limited Count` → `Tolerance`, `Zero Tolerance` → `ZeroTolerance`; Linkage logic: automatically update record value when switching strategies (Ignore→clear, ZeroTolerance→0, Tolerance→null for user to fill in) |
| errorLimit.record | Error record tolerance count. Unit: records. | Required when Tolerance | None | Y | Display condition: when errorLimit.strategy is Tolerance; Validation rule: must be a positive integer |
| failoverEnable | Auto-resume after failure. Auto-resume is an At Least Once behavior and may cause data redundancy. Only takes effect with "auto-rerun on failure"; manual reruns are not affected. | N | false | Y (conditionally displayed) | Frontend default: false; Display condition: when resource group type is DIONFLINK and both source/destination data sources are in the support list; Linkage logic: requires secondary confirmation when enabling |
| common.column.timeZone | Time zone. When left empty, the resource group's time zone is used. | N | Resource group's time zone | Y | Frontend default: resource group's time zone; Frontend options: obtained via getTimezoneList API |
| jvmMemory | Memory usage. Manually specify the task's memory usage; do not exceed the single-machine available memory, otherwise there is a risk of being unable to start. | N | 1 | Y (conditionally displayed) | Frontend default: 1; Display condition: when executeMode is distribute and the data source supports the JVM Memory plugin |


## Configuration Example

```json
{
  "speed": {
    "concurrent": 10,
    "throttle": true,
    "mbps": 20
  },
  "executeMode": "distribute",
  "errorLimit": {
    "strategy": "ZeroTolerance"
  },
  "jvmOption": "-Xms2048m -Xmx2048m",
  "jvmMemory": 2,
  "failoverEnable": true,
  "common": {
    "column": {
      "timeZone": "Asia/Shanghai"
    }
  }
}
```
