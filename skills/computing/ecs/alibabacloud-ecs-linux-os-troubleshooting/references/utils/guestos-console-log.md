# Serial Console Log Query and Analysis

This document describes how to obtain and analyze the serial console log (Serial Console Log) of an ECS instance. The serial console log is the only kernel-stage evidence source that can be obtained **without entering the instance**, so it is the first choice when GuestOS cannot start, crashes, or hangs.

## Step 1: Obtain the Serial Console Log

Use the plugin command `aliyun ecs get-instance-console-output` to call the `GetInstanceConsoleOutput` OpenAPI action. The `ConsoleOutput` field in the response is Base64-encoded, so decode it and save it to a local file before analysis:

```bash
aliyun ecs get-instance-console-output \
  --biz-region-id <region-id> \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
  | jq -r '.ConsoleOutput' | base64 -d > /tmp/<instance-id>-console.log
```

Notes:

- The serial console log is a **bounded ring buffer** that retains only the most recent output. If the abnormality happened long ago, the relevant log may already be overwritten. In that case, state this explicitly instead of concluding that "no abnormality exists".
- `LastUpdateTime` in the response indicates when the log was last updated. If it is much earlier than the abnormality time, the kernel has produced no output since then, which is itself evidence that the system is stuck or down.
- If the response is empty or the action is not supported, fall back to the VNC screenshot obtained through `GetInstanceScreenshot`.

## Step 2: Locate the Anchor Line by Keyword

Search the decoded log with the keywords for the current scenario, and use the last matching line as the analysis anchor:

```bash
grep -n -i -E '<keyword-pattern>' /tmp/<instance-id>-console.log | tail -20
```

Recommended keywords per scenario:

| Troubleshooting scenario | Recommended keyword pattern |
| --- | --- |
| Crash | `panic\|Oops\|BUG: unable to handle\|general protection fault` |
| Hang | `soft lockup\|hung_task\|blocked for more than\|watchdog` |
| OOM | `oom-killer\|Out of memory\|Killed process` |
| Startup stuck | `systemd\|Failed\|Timed out\|Dependency failed\|emergency mode` |
| File system or disk | `EXT4-fs error\|XFS.*error\|I/O error\|read-only file system` |
| Missing driver or device | `No bootable device\|Cannot open root device\|virtio\|unknown-block` |

If the user has already provided an exact abnormality time, or a time is visible in the VNC screenshot, use that timestamp to locate the anchor line directly instead of searching by keyword.

## Step 3: Expand the Context Progressively

**Trigger condition**: whenever **any abnormal log** (error, panic, failed, timeout, stack fragment, and so on) is found, you **must** expand the context around the anchor line to obtain enough information, until the root cause is fully clear.

Expand with a doubling number of context lines, for at most 4 rounds:

```bash
# Round 1: 200 lines of context. Then rounds 2 to 4 use 400, 800, and 1600.
grep -n -i -E '<keyword-pattern>' -C 200 /tmp/<instance-id>-console.log | tail -400
```

After each round, judge whether the root cause can be located:

- Can be located: stop expanding and output the conclusion together with the key log fragment as evidence.
- Cannot be located: continue with the next round.
- Still not located after round 4: mark the result as "no clear root cause found in the serial console log", and continue with the subsequent steps of the phenomenon-domain document. Do not guess a root cause based on incomplete logs.
