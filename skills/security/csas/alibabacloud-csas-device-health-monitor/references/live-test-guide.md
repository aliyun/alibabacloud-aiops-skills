# Current-Account Integration Tests

Use the live test only with an approved read-only profile and region. It never changes CSAS resources. It discovers candidate devices at runtime and does not store device tags, hostnames, usernames, or raw API responses in the skill.

Run it with explicit context:

```bash
bash tests/live/test-csas-readonly.sh --profile sase_test --region cn-hangzhou
```

Each run creates a unique temporary local directory for pagination data and the mobile-scan resume file, then removes it on exit. Concurrent runs therefore do not share local state.

The test has two data-aware paths. It probes a bounded number of recently reporting Windows or macOS candidates and runs a device report only when both CPU and memory have at least two samples. It also scans one Android device and verifies the supported mobile partial-data path. If no desktop candidate has both trends, the desktop assertion is reported as a skip rather than a fabricated pass.

These integration checks are account-specific. The `sase_test` profile is only an explicit local test configuration. Portable submission scenarios under `evals/` must use the platform's default CLI configuration and must not embed a profile name, device tag, hostname, username, or an assumed workload value from this account.
