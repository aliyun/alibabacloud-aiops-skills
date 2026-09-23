# Local Scan Resume File

The default state directory is `.device-health-state` relative to the caller's working directory.

A resume file contains `schema_version`, `generated_at`, and `processed_device_tags`. The scan updates it atomically after each attempted device. Resume files are local execution state, not cloud resources.
