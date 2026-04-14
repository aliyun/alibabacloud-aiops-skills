# Acceptance Criteria

Test patterns and verification criteria for the alibabacloud-sas-install-agent skill.

## Prerequisites

- Aliyun CLI >= 3.3.1 installed and configured
- Valid Alibaba Cloud credentials (`aliyun configure list` shows active profile)
- Security Center (SAS) service activated
- Necessary RAM permissions granted (see `references/ram-policies.md`)

## Test Scenarios

### Scenario 1: Alibaba Cloud ECS Onboarding

**Given**: A running Alibaba Cloud ECS instance that is not yet onboarded to Security Center.

**Expected flow**:
1. Skill queries ECS instance info via `describe-instances`
2. Skill queries client status via `describe-cloud-center-instances`
3. If uninstalled: Skill gets/creates install code via `describe-install-codes` / `add-install-code`
4. Skill checks cloud assistant via `describe-cloud-assistant-status`
5. If cloud assistant online: Skill dispatches install via `run-command` (after user confirmation)
6. Skill verifies agent comes online

**Acceptance**: Agent `ClientStatus` = `online` after installation.

### Scenario 2: On-Premises IDC Direct Connection

**Given**: An IDC server with public network or leased-line access to Alibaba Cloud.

**Expected flow**:
1. Skill gets/creates install code with correct VendorName (OTHER for public, ALIYUN for leased-line)
2. Skill provides appropriate install command based on network method
3. User executes manually; skill verifies onboarding

**Acceptance**: Server appears in Security Center asset list with `ClientStatus` = `online`.

### Scenario 5: Version and Feature Query

**Given**: An active Security Center subscription or pay-as-you-go instance.

**Expected flow**:
1. Skill queries version via `describe-version-config`
2. Skill queries authorization via `get-auth-summary`
3. Skill displays version, quota, expiration, module switches in readable format

**Acceptance**: All version info displayed correctly with timestamps converted to human-readable format.

### Scenario 6: Authorization Version Change

**Given**: A server with Security Center agent online, needing version upgrade.

**Expected flow**:
1. Skill queries asset status and current auth version
2. Skill confirms operation type and billing mode
3. For subscription: Skill executes `bind-auth-to-machine` (after secondary confirmation)
4. For pay-as-you-go: Skill executes `update-post-paid-bind-rel` (after secondary confirmation with cost estimate)
5. Skill verifies version change

**Acceptance**: Asset's `AuthVersion` updated to target version.

### Scenario 8: Agent Uninstall

**Given**: A server with Security Center agent online.

**Expected flow**:
1. Skill queries asset info to get UUID
2. Skill displays uninstall details with warnings
3. After explicit confirmation, executes `add-uninstall-clients-by-uuids`
4. Verifies agent is offline/removed

**Acceptance**: Agent `ClientStatus` changes to `offline` or asset removed from list.

### Scenario 9: Security Risk Detection

**Given**: A server with Security Center agent online and paid version bound.

**Expected flow**:
1. For targeted scan: Skill auto-checks prerequisites (auth + client)
2. Skill dispatches security check via `modify-push-all-task`
3. Skill dispatches virus scan via `create-virus-scan-once-task` chain
4. Skill polls progress via `describe-once-task` / `get-virus-scan-latest-task-statistic`
5. After completion, skill queries and displays risk results

**Acceptance**: Risk results displayed (vulnerabilities, baseline, alerts, virus scan) after scan completion.

## Cross-Cutting Checks

| Check | Criteria |
|-------|----------|
| CLI format | All commands use plugin mode (kebab-case), not PascalCase |
| User-agent | All `aliyun` commands include `--user-agent AlibabaCloud-Agent-Skills` |
| Write confirmation | All write operations display details and wait for user confirmation |
| Credential safety | No AK/SK values are ever printed or exposed |
| Permission errors | On 403/NoPermission, skill reads `ram-policies.md` and guides user |
| Parameter confirmation | User-customizable parameters are confirmed before execution |
