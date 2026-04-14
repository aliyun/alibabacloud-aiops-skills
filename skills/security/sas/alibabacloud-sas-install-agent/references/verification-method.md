# Success Verification Methods

Verification methods for each scenario to confirm successful completion.

## Installation Scenarios

### Scenario 1: ECS Onboarding

```bash
aliyun sas describe-cloud-center-instances \
  --criteria '[{"name":"instanceId","value":"<instance-id>"}]' \
  --machine-types ecs \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: `ClientStatus` = `online`

### Scenario 2: IDC Direct Connection

```bash
aliyun sas describe-cloud-center-instances \
  --criteria '[{"name":"internetIp","value":"<server-IP>"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: Server found in asset list with `ClientStatus` = `online`

If not found, sync assets first:
```bash
aliyun sas refresh-assets --asset-type ecs --user-agent AlibabaCloud-Agent-Skills
```

### Scenario 3: Image-Based Installation

After new instance boots from image, wait ~5 minutes:

```bash
aliyun sas describe-cloud-center-instances \
  --criteria '[{"name":"instanceId","value":"<new-instance-id>"}]' \
  --machine-types ecs \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: New instance appears with `ClientStatus` = `online` and unique UUID

## Management Scenarios

### Scenario 5: Version Query

**Success criteria**: Version info, authorization quota, and module switches displayed in readable format. Timestamps converted from 13-digit to YYYY-MM-DD HH:mm:ss.

### Scenario 6: Authorization Change

```bash
aliyun sas describe-cloud-center-instances \
  --criteria '[{"name":"instanceId","value":"<instance-id>"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: `AuthVersion` matches the target version number

### Scenario 7: Software Query

**Success criteria**: `describe-property-sca-detail` returns matching software entries with server details

### Scenario 8: Agent Uninstall

```bash
aliyun sas describe-cloud-center-instances \
  --criteria '[{"name":"uuid","value":"<UUID>"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: `ClientStatus` changed to `offline` or asset no longer in list

### Scenario 9: Security Risk Detection

**Vulnerability scan completion**:
```bash
aliyun sas describe-once-task --task-type "VUL_CHECK_TASK" --current-page 1 --page-size 1 --user-agent AlibabaCloud-Agent-Skills
```
**Success criteria**: Latest task `TaskStatusText` != `PROCESSING`

**Baseline check completion**:
```bash
aliyun sas describe-strategy --strategy-ids "<id>" --user-agent AlibabaCloud-Agent-Skills
```
**Success criteria**: `ExecStatus` = 1 (completed)

**Virus scan completion**:
```bash
aliyun sas get-virus-scan-latest-task-statistic --user-agent AlibabaCloud-Agent-Skills
```
**Success criteria**: `Status` = 20 (completed)

## Local Server Verification

### Linux
```bash
ps -ef | grep -E 'AliYunDun|YunDunMonitor|YunDunUpdate'
systemctl status aegis
```

### Windows (PowerShell)
```powershell
Get-Process | Where-Object {$_.Name -match '^(AliYunDun|AliYunDunMonitor|AliYunDunUpdate)$'}
Get-Service | Where-Object {$_.Name -match 'Aegis|AliYunDun'}
```

### Network Connectivity
```bash
telnet jsrv.aegis.aliyun.com 80
telnet update.aegis.aliyun.com 443
```
