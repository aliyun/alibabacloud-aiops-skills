# Security Center Agent Install Guide

## TOC

- [Prerequisites and Preparation](#prerequisites-and-preparation)
- [Installation Method Selection](#installation-method-selection)
- [Installation Steps](#installation-steps)
- [Verify Installation Status](#verify-installation-status)
- [Network Connectivity Requirements](#network-connectivity-requirements)
- [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)

---

## Prerequisites and Preparation

1. **System requirements**: OS must be within the supported range.
2. **Account restriction**: Only supports servers under the current Alibaba Cloud account; cross-account requires multi-account management.
3. **Resource estimate**: Single installation takes approximately 5 minutes; CPU/memory may briefly spike during high-load tasks; no business restart required.
4. **Clean residuals**: If previously installed, uninstall first and manually delete directories:
   - Linux: `/usr/local/aegis`
   - Windows: `C:\Program Files (x86)\Alibaba\Aegis`
5. **Network policy**: Ensure firewall/security group allows outbound traffic to Security Center service IPs or domains (ports 80/443).

---

## Installation Method Selection

| Method | Applicable Scenario | Core Advantage |
|--------|---------------------|----------------|
| One-click install | Running ECS with cloud assistant, VPC network, supported region | Console operation, no server login needed |
| General install | Any server with public network access (Alibaba Cloud ECS or external hosts) | Compatible with mainstream OS, flexible configuration |
| Image batch install | Scale-out creation of new servers with pre-installed agent | One-time setup, batch reuse |
| Network-restricted install | Cannot connect to public network directly, requires proxy or custom endpoint | Adapts to complex network environments |

---

## Installation Steps

### 1. One-Click Install (via Cloud Assistant)

**Prerequisites**:
- ECS status is "Running" with cloud assistant installed
- Network type is VPC (Virtual Private Cloud)
- Region is in the supported list (e.g. Hangzhou, Shanghai, Beijing, Shenzhen, Singapore, Frankfurt, etc.)
- Third-party security software has been closed

**Procedure**:
1. Log into the Security Center console
2. Left navigation: **System Settings > Feature Settings**, select region (Mainland China / Non-Mainland China)
3. **Client > Uninstalled Client** tab, click **Install Client** in the target server's action column
4. Multi-select servers and click **One-Click Install** for batch deployment

### 2. General Install (Manual Command Execution)

**Procedure**:
1. Obtain install command (via console or API `describe-install-codes` / `add-install-code`)
2. Select the corresponding command based on server OS and network access method
3. Log into the server and execute the command with admin privileges

> Install code (`-k=` parameter) is obtained via the describe-install-codes API. Different access methods correspond to different install codes.

> **Installation process note**: The install command takes some time to execute. Intermediate error messages during the process can be ignored. Success is determined by the final output -- as long as it shows installation succeeded, the process is complete.

#### Linux Install Commands

**Alibaba Cloud internal network access**:
```bash
wget "https://update2.aegis.aliyun.com/download/install/2.0/linux/AliAqsInstall.sh" && chmod +x AliAqsInstall.sh && ./AliAqsInstall.sh -k=<install-code>
```

**Public network access**:
```bash
wget "https://aegis.alicdn.com/download/install/2.0/linux/AliAqsInstall.sh" && chmod +x AliAqsInstall.sh && ./AliAqsInstall.sh -k=<install-code>
```

#### Windows Install Commands

**CMD - Alibaba Cloud internal network access**:
```cmd
powershell -executionpolicy bypass -c "(New-Object Net.WebClient).DownloadFile('https://update2.aegis.aliyun.com/download/install/2.0/windows/AliAqsInstall.exe', $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath('.\AliAqsInstall.exe'))"; "./AliAqsInstall.exe -k=<install-code>"
```

**CMD - Public network access**:
```cmd
powershell -executionpolicy bypass -c "(New-Object Net.WebClient).DownloadFile('https://aegis.alicdn.com/download/install/2.0/windows/AliAqsInstall.exe', $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath('.\AliAqsInstall.exe'))"; "./AliAqsInstall.exe -k=<install-code>"
```

**PowerShell - Alibaba Cloud internal network access**:
```powershell
(New-Object Net.WebClient).DownloadFile('https://update2.aegis.aliyun.com/download/install/2.0/windows/AliAqsInstall.exe', $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath('.\AliAqsInstall.exe')); ./AliAqsInstall.exe -k=<install-code>
```

**PowerShell - Public network access**:
```powershell
(New-Object Net.WebClient).DownloadFile('https://aegis.alicdn.com/download/install/2.0/windows/AliAqsInstall.exe', $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath('.\AliAqsInstall.exe')); ./AliAqsInstall.exe -k=<install-code>
```

#### Download Domain Reference

| Access Method | Download Domain | Description |
|--------------|-----------------|-------------|
| Alibaba Cloud internal | `update2.aegis.aliyun.com` | Via Alibaba Cloud internal network or leased line |
| Public network | `aegis.alicdn.com` | Via public internet |

### 3. Image Batch Install

**Procedure**:
1. Prepare a clean template server (no third-party security software)
2. When obtaining install command, configure **Create Image System: Yes** (`OnlyImage=true`)
3. Execute the command on the template server (downloads files but does not start the service)
4. **Shut down immediately** (do not restart); create a custom image from this server
5. New instances created from this image will automatically activate and generate a unique ID on first boot

> Warning: Before making multiple images from the same template, you must uninstall, clean, and re-obtain the command each time to avoid UUID conflicts.

### 4. Network-Restricted or Complex Environment Install

#### A. Overseas Hosts or Unstable Network

**Linux**:
```bash
wget "https://update6.aegis.aliyun.com/download/install/2.0/linux/AliAqsInstall.sh" && chmod +x AliAqsInstall.sh && ./AliAqsInstall.sh "-j=jsrv-abroad.aegis.aliyuncs.com|jsrv.aegis.aliyun.com" "-u=aegis.alicdn.com|update6.aegis.aliyun.com|update.aegis.aliyun.com" -k=<install-code>
```

**Windows CMD**:
```cmd
powershell -executionpolicy bypass -c "(New-Object Net.WebClient).DownloadFile('https://update6.aegis.aliyun.com/download/install/2.0/windows/AliAqsInstall.exe', $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath('.\AliAqsInstall.exe'))"; "./AliAqsInstall.exe '-j=jsrv-abroad.aegis.aliyuncs.com|jsrv.aegis.aliyun.com' '-u=aegis.alicdn.com|update6.aegis.aliyun.com|update.aegis.aliyun.com' -k=<install-code>"
```

#### B. Alibaba Cloud Internal Leased Line Access

**Linux**:
```bash
wget "https://update2.aegis.aliyun.com/download/install/2.0/linux/AliAqsInstall.sh" && chmod +x AliAqsInstall.sh && ./AliAqsInstall.sh "-j=jsrv2.aegis.aliyun.com|jsrv3.aegis.aliyun.com|jsrv4.aegis.aliyun.com|jsrv5.aegis.aliyun.com|jsrv.aegis.aliyun.com" "-u=update2.aegis.aliyun.com|update4.aegis.aliyun.com|update5.aegis.aliyun.com|update3.aegis.aliyun.com|aegis.alicdn.com|update.aegis.aliyun.com" -k=<install-code>
```

**Windows CMD**:
```cmd
powershell -executionpolicy bypass -c "(New-Object Net.WebClient).DownloadFile('https://update2.aegis.aliyun.com/download/install/2.0/windows/AliAqsInstall.exe', $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath('.\AliAqsInstall.exe'))"; "./AliAqsInstall.exe '-j=jsrv2.aegis.aliyun.com|jsrv3.aegis.aliyun.com|jsrv4.aegis.aliyun.com|jsrv5.aegis.aliyun.com|jsrv.aegis.aliyun.com' '-u=update2.aegis.aliyun.com|update4.aegis.aliyun.com|update5.aegis.aliyun.com|update3.aegis.aliyun.com|aegis.alicdn.com|update.aegis.aliyun.com' -k=<install-code>"
```

#### C. Multi-Cloud Environment with Internal IP Conflicts

**Linux**:
```bash
wget "https://aegis.alicdn.com/download/install/2.0/linux/AliAqsInstall.sh" && chmod +x AliAqsInstall.sh && ./AliAqsInstall.sh "-j=jsrv.aegis.aliyun.com" "-u=aegis.alicdn.com|update.aegis.aliyun.com" -k=<install-code>
```

---

## Verify Installation Status

### Console Verification (approximately 5-minute delay)
- Alibaba Cloud servers: **Client** column icon changes from "Unprotected" to "Protected"
- Non-Alibaba Cloud servers: Appears in the list with icon change; if not showing, click **Sync Latest Assets**

### Local Server Verification (real-time)

**Check processes**:

Linux:
```bash
ps -ef | grep -E 'AliYunDun|YunDunMonitor|YunDunUpdate'
systemctl status aegis
```

Windows (PowerShell):
```powershell
Get-Process | Where-Object {$_.Name -match '^(AliYunDun|AliYunDunMonitor|AliYunDunUpdate)$'}
Get-Service | Where-Object {$_.Name -match 'Aegis|AliYunDun'}
```

**Check network connectivity**:
```bash
telnet jsrv.aegis.aliyun.com 443
telnet update.aegis.aliyun.com 443
```

---

## Network Connectivity Requirements

### Aegis Server (Message Channel)

The agent uses TCP protocol to connect to port 80 for message channel dispatch and data reporting. At least one group of domains must have port 80 connectivity.

| Domain | VIP | Description |
|--------|-----|-------------|
| jsrv.aegis.aliyun.com | 47.117.157.227, 8.153.161.116, 8.153.86.12, 106.14.18.21 | China mainland public domain |
| jsrv2.aegis.aliyun.com | 100.100.30.25, 100.100.30.26 | China mainland Alibaba Cloud internal (leased line) domain |

---

## Common Issues and Troubleshooting

- **Third-party software conflict**: Close antivirus/EDR software before installation; can be restored after installation.
- **Self-protection process interference**: If prompted "self-protection is running", restart the server and reinstall.
- **Agent offline troubleshooting**:
  - Restart processes (Linux: `killall` + start latest version; Windows: restart service)
  - Check DNS, firewall ACL, security group outbound rules
  - Check disk/CPU/memory resources
  - Verify `aegis_client.conf` does not have duplicate UUIDs
  - Check logs: Linux `/usr/local/aegis/aegis_client/aegis_12_xx/data/`, Windows `C:\Program Files (x86)\Alibaba\Aegis\aegis_client\aegis_12_xx\data\`
