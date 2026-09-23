# CSAS API Contract

The script uses plugin-mode Alibaba Cloud CLI commands only: `list-user-devices`, `get-user-device`, and `get-user-device-workload-trend`.

`list-devices` is the script-managed discovery command and returns each candidate's exact DeviceTag, hostname, device type, DeviceStatus, and UpdateTime. `list-user-devices` resolves an exact DeviceTag first (including non-UUID tags) and then resolves an exact hostname to one device tag. `get-user-device` provides battery, disk, collection time, and device identity fields. `get-user-device-workload-trend` requires `device-tag`, `workload-type`, `from`, and `to`; `workload-type` is `cpu` or `mem`.

The report returns `device_status` from CSAS and separately labels collection time as `recently_reporting`, `stale_or_unparseable`, or `insufficient_data` for the requested window. Zero, negative, malformed, and non-10-digit numeric timestamps are `insufficient_data`; they are never parsed as current time. Collection status is a reporting-recency indicator, not a claim of real-time network connectivity.

Disk usage is calculated only when `DiskUsed + DiskAvailable` is positive. A zero battery reading with no valid collection time and no disk capacity is `insufficient_data`, with `snapshot_status: critical` retained as raw-rule evidence. Workload data is sorted by timestamp before streak calculation. A gap greater than the configured maximum (900 seconds by default) or a below-threshold point ends a streak. A missing or empty sequence is `insufficient_data`.

The report excludes raw process lists because they can be large and do not authoritatively represent device-wide CPU or memory usage.
