# Acceptance Criteria

## Correct Behavior

- `device-report` returns disk, battery, device identity, CSAS device status, collection status, CPU, and memory sections without raw process arrays.
- A single workload breach is `observation`; a streak meeting the configured consecutive count is `warning`.
- Disk usage at 95 percent or higher and battery health below 60 are `critical`.
- Empty trends, Android/iOS/Harmony trends, zero or malformed collection times, and zero-capacity disks are `insufficient_data`.
- A zero battery reading without valid collection-time and capacity evidence is `insufficient_data`; its raw threshold result may be retained in `snapshot_status`.

## Incorrect Behavior

- Treating no workload samples as healthy is incorrect.
- Calling a CSAS write action, requesting broad permissions, or exposing credential values is incorrect.
- Using PascalCase CLI commands or omitting the manifest-derived user agent is incorrect.
- Writing local audit artifacts is outside this skill's scope.
