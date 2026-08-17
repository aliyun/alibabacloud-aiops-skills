# ECS Linux Diagnosis Report

## 1. Basic Information

| Item | Value |
| --- | --- |
| Instance ID | `i-xxxxxxxx` |
| Region | `cn-xxx` |
| Instance type | `ecs.xxx` |
| Image | `<imageId> / <OS name and version>` |
| Phenomenon domain category | `<Startup issue / Usage issue / Crash or hang issue / Performance issue / ...>` |
| Phenomenon domain | `<The instance is already in the Running state, but GuestOS has not started normally / ...>` |
| Report time | `YYYY-MM-DD HH:MM` |

## 2. Problem Description

- **User's original description**: <Restate the original text in 1 to 3 sentences>
- **Clarified problem**: <Normalized phenomenon description>

## 3. Troubleshooting Process and Evidence Chain

> Record "what was checked, what was found, and what was concluded" in investigation order, so that the reader can follow the reasoning path from symptom to root cause.

| Check item | Finding | Conclusion |
| --- | --- | --- |
| <for example, "serial console log"> | <key log fragment or data> | <points to or rules out a root cause> |
| <for example, "disk inode utilization"> | <`df -i` shows /var at 100%> | <inode exhaustion confirmed> |

## 4. Root Cause

- **Root cause 1**: <One-sentence characterization, for example: "The data disk containing `/var` has exhausted its inodes, causing sshd to fail when writing temporary files">
  - Evidence: <The key findings in section 3 that support this root cause>
- **Root cause 2** (if any, otherwise delete this line): <...>

> When multiple root causes exist, explain their relationship: whether one root cause led to another, or whether several root causes acted together.

## 5. Remediation and Mitigation Recommendations

### 5.1 Immediate Fix

1. **<Action description, explaining in one sentence what this step does>**

   ```bash
   <complete command>
   ```

   Expected result: <what should be observed after execution, for example "inode utilization drops and sshd logon succeeds">

2. ...

### 5.2 Long-Term Mitigation

- <Preventive measures for configuration, monitoring, capacity, versions, and other aspects>
