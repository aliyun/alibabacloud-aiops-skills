# Operational Limits

Fleet scan defaults to seven days and no more than 100 devices. Eligible desktop devices require one detail call and two workload calls. Android, iOS, and Harmony devices, plus desktops without a recent `UpdateTime`, receive only the snapshot evaluation and an `insufficient_data` workload result.

The scan is serial by default and accepts `--delay-seconds`. Use `--resume-file` for restartable batches. Each transient CSAS failure is retried at most four times with bounded exponential backoff. Permission, invalid-input, and other non-transient failures are not retried and are reported as partial results.
