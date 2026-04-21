# javamem (Java Memory Diagnosis)

> Parameter notes are based on `service_scripts/javamem_pre.py`.

## Overview

Runs SysOM javamem on a target **Java process**, producing **`javamem.json`** for JVM memory analysis.

## When to Use (Agent)

- Java application memory pressure, heap issues, or JNI profiling scenarios requiring cloud-side collection.

## `params` Fields

| Field | Type | Required | Meaning | Default | Notes |
|------|------|------|------|------|------|
| `region` | string | yes* | Region | — | `--region` |
| `instance` | string | yes* | Instance ID | — | `--instance` |
| `pod` | string | no | Pod name | — | requires at least one of `pod` or `pid` |
| `Pid` or `pid` | string/int | conditional | Java process PID | — | **at least one of `pod` and `pid` is required** |
| `duration` | int | no | profiling duration in **minutes** | `"0"` | `0` means no profiling append |

### Validation

- If **both `pod` and `pid` are missing**, service returns invalid params.

## Platform Constraints

| Item | Value |
|----|-----|
| support_channel | **all** |
| support_mode | **all** |
| minimum version | common baseline **`3.8.0-beta`** |

## Recommended Usage

Run in `sysom-diagnosis/` (skill root):

```bash
./scripts/osops.sh memory javamem --deep-diagnosis --channel ecs \
  --region cn-hangzhou --instance i-xxx \
  --params '{"pid":12345,"duration":5}'
```

Use `--params-file` for complex payloads (`pid` / `pod` / `duration`). Increase `--timeout` for long-running collections.
