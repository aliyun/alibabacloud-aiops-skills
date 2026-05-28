# Lessons Learned — Deployment Failure Patterns & Fixes

> This document is auto-populated by the batch deployment test (see `tests/batch-deploy-100.md`).
> When an Agent encounters a deployment issue, it SHOULD consult this file first for known
> patterns and proven fixes before attempting ad-hoc troubleshooting.

## How to Use This File

1. **Before deploying**: Skim the error signatures below. If the project matches a known
   trigger scenario, apply the fix proactively.
2. **After a failure**: Search this file for the error message or signature. If found,
   apply the documented fix and retry.
3. **Contributing new lessons**: When a new failure pattern is observed >= 2 times across
   different projects, add a new entry following the format below.

## Entry Format

Each lesson follows this structure:

```markdown
### <Error Signature>

- **Phase**: check / init / deploy / verify
- **Trigger Scenario**: <what type of project or condition triggers this>
- **Symptom**: <exact error message or observable behavior>
- **Root Cause**: <why it happens>
- **Fix**: <what the Agent should do — specific commands or decision changes>
- **Affected Projects**: <list of test project numbers/names that hit this>
- **First Observed**: <date or test round>
```

---

## Lessons

(The following entries are auto-appended by the Agent during batch deployment testing.
Do not manually edit below this line unless correcting an inaccuracy.)

---

### `Java-Build-Use-Release-JAR`

- **Phase**: deploy / verify
- **Trigger Scenario**: Spring Boot or any Java/Gradle/Maven project on 2C4G ECS where `appmanager init` generated a default start script and the project requires `mvn package` / `gradle bootJar` to produce a runnable JAR.
- **Symptom**:
  - Round 1: `Error: Unable to access jarfile *.jar` (default `java -jar *.jar` finds no JAR in the cloned source tree).
  - Round 2 (if Agent retries with `gradle bootJar`): `ReleaseFailed` or `ReleaseCancelled` after the 15-minute deploy budget elapses; `gradle clean bootJar` typically OOM's or runs >15 min on 2 vCPU + 4 GiB RAM.
- **Root Cause**: 2C4G is too small to build large Java projects in the deploy window.
- **Fix**: Skip source build. Replace `common.scripts.start` with:
  ```yaml
  common:
    scripts:
      start: |
        : > /root/app.log
        mkdir -p /root && cd /root
        if [ ! -f halo.jar ]; then
          curl -fSL "https://github.com/halo-dev/halo/releases/download/v2.20.12/halo-2.20.12.jar" -o /root/halo.jar
        fi
        pkill -f 'halo.jar' || true
        nohup java -Xmx384m -jar /root/halo.jar --server.port=8090 >> /root/app.log 2>&1 &
  ```
  Always set `-Xmx` ≤ 384 m (heap > 50 % of 4 GiB triggers OOM-killer when paired with the JVM's other memory regions).
- **Affected Projects**: #1 halo (validated Round 3 SUCCESS); also recommended for #81 spring-petclinic, #85 stirling-pdf.
- **First Observed**: Batch Round 1 (#1 halo Round 1).

---
