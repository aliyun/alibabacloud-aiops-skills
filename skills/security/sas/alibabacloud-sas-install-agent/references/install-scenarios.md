# Installation Scenario Detailed Steps

## TOC

- [Scenario 1: Alibaba Cloud ECS Onboarding](#scenario-1-alibaba-cloud-ecs-onboarding)
- [Scenario 2: On-Premises IDC Direct Connection](#scenario-2-on-premises-idc-direct-connection)
- [Scenario 3: Image-Based Batch Installation](#scenario-3-image-based-batch-installation)
- [Scenario 4: Network Troubleshooting](#scenario-4-network-troubleshooting)

---

## Scenario 1: Alibaba Cloud ECS Onboarding

### Step 1: Get User's ECS Information

Ask the user for ECS details (instance ID, IP address, region, etc.), then query instance status:

```bash
aliyun ecs describe-instances --region <RegionId> --biz-region-id <RegionId> --instance-ids '["<instance-id>"]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

> **[MUST] ECS API Region parameter rules**:
> - The parameter name is `--biz-region-id` (NOT `--RegionId`, `--region-id`, or `--Region`). Using the wrong parameter name causes `unknown flag` errors.
> - When the region comes from a SAS `describe-cloud-center-instances` response, use the `RegionId` field (e.g. `cn-hangzhou`), NOT the `Region` field (e.g. `cn-hangzhou-dg-a01`). The `Region` field contains the physical availability zone identifier which is not recognized by standard ECS APIs and causes `InvalidInstance.NotFound` or `RegionId.ApiNotSupported` errors.
> - **[MUST] Endpoint routing**: When the target instance's region differs from the CLI's default configured region, you MUST also add `--region <RegionId>` to route the request to the correct ECS endpoint. `--biz-region-id` only sets the RegionId parameter in the request body but does NOT change the API endpoint. Without `--region`, the request goes to the default region's endpoint and returns `InvalidOperation.NotSupportedEndpoint`. Example: `aliyun ecs describe-instances --region cn-hangzhou --biz-region-id cn-hangzhou ...`
> - These rules apply to ALL ECS API calls in this skill: `describe-instances`, `describe-cloud-assistant-status`, `run-command`, `describe-invocation-results`.

### Step 2: Query Client Status

```bash
aliyun sas describe-cloud-center-instances --criteria '[{"name":"instanceId","value":"<instance-id>"}]' --machine-types ecs --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Evaluate based on `ClientStatus` and `ClientSubStatus`:

- **Instance not found** -> Execute `refresh-assets` to sync assets, then re-query:
  ```bash
  aliyun sas refresh-assets --asset-type ecs --vendor 0 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
  ```

- **`ClientStatus` = `online`** -> Inform the user this ECS is already onboarded and online; no action needed.

- **`ClientStatus` = `offline`, `ClientSubStatus` = `uninstalled`** -> Agent was never installed; proceed to Step 3.

- **`ClientStatus` = `offline`, `ClientSubStatus` is not `uninstalled`** (empty or other values) -> Agent is installed but offline. Suggest:
  1. Check network connectivity (refer to Scenario 4)
  2. Check if agent processes exist
  3. If unable to self-resolve, recommend submitting a support ticket

- **Not installed** (ClientStatus is empty or missing) -> Proceed to Step 3

### Step 3: Get or Create Install Code

Follow the "Common Flow: Get or Create Install Code" in SKILL.md. Recommended matching criteria: Os matches the ECS system, VendorName=ALIYUN, OnlyImage=false.

### Step 4: Determine Installation Method

Query cloud assistant status:
```bash
aliyun ecs describe-cloud-assistant-status --region <RegionId> --biz-region-id <RegionId> --instance-id "<instance-id>" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Cloud assistant online** (`CloudAssistantStatus=true`) -> Display install command content, dispatch remotely via cloud assistant after confirmation:

Linux:
```bash
aliyun ecs run-command \
  --region <RegionId> \
  --biz-region-id <RegionId> \
  --type RunShellScript \
  --command-content "<Base64-encoded-install-command>" \
  --instance-id "<instance-id>" \
  --content-encoding Base64 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Windows:
```bash
aliyun ecs run-command \
  --region <RegionId> \
  --biz-region-id <RegionId> \
  --type RunPowerShellScript \
  --command-content "<Base64-encoded-install-command>" \
  --instance-id "<instance-id>" \
  --content-encoding Base64 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Cloud assistant not online** -> Display install command and guide the user to log into the server and execute manually:

Linux (root privileges, Alibaba Cloud internal network):
```bash
wget "https://update2.aegis.aliyun.com/download/install/2.0/linux/AliAqsInstall.sh" && chmod +x AliAqsInstall.sh && ./AliAqsInstall.sh -k=<install-code>
```

Windows CMD (administrator privileges, Alibaba Cloud internal network):
```cmd
powershell -executionpolicy bypass -c "(New-Object Net.WebClient).DownloadFile('https://update2.aegis.aliyun.com/download/install/2.0/windows/AliAqsInstall.exe', $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath('.\AliAqsInstall.exe'))"; "./AliAqsInstall.exe -k=<install-code>"
```

Windows PowerShell (administrator privileges, Alibaba Cloud internal network):
```powershell
(New-Object Net.WebClient).DownloadFile('https://update2.aegis.aliyun.com/download/install/2.0/windows/AliAqsInstall.exe', $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath('.\AliAqsInstall.exe')); ./AliAqsInstall.exe -k=<install-code>
```

> Alibaba Cloud ECS defaults to internal network access (`update2.aegis.aliyun.com`). For public network access, replace the download domain with `aegis.alicdn.com`.

> **Installation process note**: The install command takes some time to execute. Intermediate error messages during the process can be ignored. Success is determined by the final output -- as long as it shows installation succeeded, the process is complete.

### Step 5: Verify Onboarding

Guide the user to wait approximately 5 minutes, then re-query client status to confirm it is online.

---

## Scenario 2: On-Premises IDC Direct Connection

### Step 1: Get or Create Install Code

Follow the "Common Flow: Get or Create Install Code". Recommended matching criteria: Os matches user's server system, VendorName auto-determined by network type (leased line=ALIYUN, public=OTHER), OnlyImage=false.

### Step 2: Provide Install Command

Select the appropriate install command based on network situation (refer to `agent-install-guide.md`):

- **Public network direct** -> Standard install command
- **Leased line access** -> Install command using internal domain
- **Overseas / unstable network** -> Install command using overseas domain

Display the full command and guide the user to execute with admin privileges.

### Step 3: Verify Onboarding

Ask the user to provide the installed server's IP, then query status:
```bash
aliyun sas describe-cloud-center-instances --criteria '[{"name":"internetIp","value":"<IP-address>"}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

If not found, sync assets first then retry:
```bash
aliyun sas refresh-assets --asset-type ecs --vendor 1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

---

## Scenario 3: Image-Based Batch Installation

### Step 1: Confirm Template Server Info

Ask the user to confirm: template server instance ID/IP/region, OS, server type, network access method.

Remind the user:
- Template server must be a **clean environment**; close third-party security software (antivirus/EDR) beforehand
- If the agent was previously installed, **uninstall and clean residual directories** first:
  - Linux: `/usr/local/aegis`
  - Windows: `C:\Program Files (x86)\Alibaba\Aegis`

### Step 2: Get or Create Image-Specific Install Code

Follow the "Common Flow: Get or Create Install Code". Recommended matching criteria: Os matches template server system, VendorName matches server type, `OnlyImage=true`.

### Step 3: Provide Install Command with Critical Caveats

Select the appropriate install command based on network access method (refer to `agent-install-guide.md`). Display the full command and **emphasize these key points**:

1. Execute the install command on the template server with admin privileges
2. The command **only downloads files without starting the service** (`OnlyImage=true` install code achieves this)
3. **Shut down immediately after execution -- do not restart the template server**
4. Create a custom image from this server
5. New instances created from this image will automatically activate the agent and generate a unique ID on first boot

### Step 4: Important Warnings

Clearly inform the user about these risks:
- If making multiple images from the same template, each time you must **re-uninstall, clean, get new install code, and re-execute the install command** -- otherwise UUID conflicts will occur
- After executing the install command on the template server, it can **only be shut down**, never restarted, because restarting activates the agent and occupies the UUID
- If the template server is accidentally restarted, uninstall the agent, clean residual directories, get a new install code, and redo the process

### Step 5: Verify Onboarding

After the new instance created from the image boots up, wait approximately 5 minutes. Once the user provides the new instance info, query client status:
```bash
aliyun sas describe-cloud-center-instances --criteria '[{"name":"instanceId","value":"<new-instance-id>"}]' --machine-types ecs --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

---

## Scenario 4: Network Troubleshooting

### Required Network Access

Servers must reach the Security Center service endpoint via TCP port 80:

| Domain | VIP | Description |
|--------|-----|-------------|
| jsrv.aegis.aliyun.com | 47.117.157.227, 8.153.161.116, 8.153.86.12, 106.14.18.21 | China mainland public domain |
| jsrv2.aegis.aliyun.com | 100.100.30.25, 100.100.30.26 | China mainland Alibaba Cloud internal (leased line) domain |

### Network Connectivity Test Commands

```bash
telnet jsrv.aegis.aliyun.com 80
telnet update.aegis.aliyun.com 443
```

### Common Causes

- Firewall / security group not allowing outbound traffic
- DNS unable to resolve domain
- Server cannot access public network and no leased line configured

### Further Troubleshooting

- Check agent processes: `ps -ef | grep -E 'AliYunDun|YunDunMonitor'`
- Check logs: `/usr/local/aegis/aegis_client/aegis_12_xx/data/`
- If unable to self-resolve, recommend submitting a support ticket
