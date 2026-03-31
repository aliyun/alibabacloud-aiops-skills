# Mount App Installation Guide

## Overview

mountapp is a PDS cloud drive mount plugin that supports mounting PDS cloud drive storage to local computer, allowing access to files in PDS cloud drive like local files. It supports Windows, macOS, and Linux systems.
The following sections describe the download, installation, startup, and mounting process of the mount app, including:
- Get plugin latest version and download URL
- Download software installation package
- Execute installation process
- Start mount app
- Complete mounting
- Verify installation results
- Query mount app status
- Query mount configuration
- Modify mount app configuration

## Prerequisites
Before installing mount app, verify that aliyun-cli and PDS plugin are installed and configured correctly

---

## Workflow

### Step 1: Check if Mount App is Already Installed and Running

Check if installed:
- **Windows/macOS systems**:
  - Check if there are mountapp related files in `~/.edm/plugins/mountapp` directory
  - View version number via `~/.edm/plugins/mountapp/plugin.json`

If already installed, view the plugin configuration in mountapp directory to get the installed version number:

```json
{
  "id": "mountapp",
  "name": "mountapp",
  "version": "0.8.2",
  "manifest_version": "v2",
  "client_id": "GzpsX2VzKLNKNsxProd",
  "redirect_uri": "https://web-sv.aliyunpds.com/plugin_callback",
  "scripts": {
    "start": "chmod +x bin/start.sh;bin/start.sh ${port} ${user_id}",
    "install": "chmod +x bin/install.sh;bin/install.sh",
    "upgrade": "chmod +x bin/upgrade.sh;bin/upgrade.sh",
    "stop": "chmod +x bin/stop.sh;bin/stop.sh",
    "uninstall": "chmod +x bin/uninstall.sh;bin/uninstall.sh"
  }
}
```

For example, the `version` field in the above configuration is the installed version number.

- **Linux systems**:
  - Check if there are mountapp related files in `/opt/mountapp` directory
  - View service list via `systemctl list-units --type=service | grep mountapp`
  - View service status via `systemctl status mountapp`
  - View installed rpm packages via `rpm -qa | grep mountapp`
  - View installed dpkg packages via `dpkg -s mountapp`

---

### Step 2: Get Mount App Plugin Download URL

Use command line tool to get the latest mount app version:

```bash
aliyun pds mountapp --action get-latest-version --user-agent AlibabaCloud-Agent-Skills
```

Response format:
```json
{
  "version": "0.8.2",
  "url": "https://example.com/mountapp-0.8.2.zip"
}
```

**Version comparison logic**:
- If installed version matches latest version, skip Step 3 and go directly to Step 6
- If installed version differs from latest version, continue with Step 3 to download latest installation package
- If not installed locally, proceed to Step 3 to download latest installation package

---

### Step 3: Download Installation Package

Based on current operating system and download URL from Step 2, download mount app plugin installation package to temporary directory.

Different operating systems require different installation package types:
- **Windows**: zip
- **macOS**: zip
- **Linux**: rpm

**Download command example**:

```bash
# Get download URL
latest_info=$(aliyun pds mountapp --action get-latest-version --user-agent AlibabaCloud-Agent-Skills)
download_url=$(echo "$latest_info" | jq -r '.url')
version=$(echo "$latest_info" | jq -r '.version')

# Download to temporary directory
curl --max-time 600 -fL -o "/tmp/mountapp-${version}.zip" "$download_url"  # Windows/macOS
curl --max-time 600 -fL -o "/tmp/mountapp-${version}.rpm" "$download_url"  # Linux
```

---

### Step 4: Execute Installation

Execute installation based on operating system and installation package type:

#### Windows Installation

1. **Extract ZIP package**:

```powershell
# Extract to ~/.edm/plugins/
Expand-Archive -Path "$env:TEMP\mountapp-${version}.zip" -DestinationPath "$env:USERPROFILE\.edm\plugins\" -Force
```

2. **Install Dokan Driver**:
Before installing Dokan driver, check if already installed using cmd query command:
```
sc query dokan1
```
**Expected output**: If service status is displayed (RUNNING or STOPPED), it is installed; if service does not exist, Dokan driver needs to be installed.


```powershell
# Use extracted Dokan MSI installation file
$dokanInstaller = "$env:USERPROFILE\.edm\plugins\mountapp\pkg\Dokan_x64-noVC.msi"
Start-Process msiexec.exe -ArgumentList "/i `"$dokanInstaller`" /qn /norestart" -Wait -Verb RunAs
```

#### macOS Installation

1. **Extract ZIP package**:

```bash
# Extract to ~/.edm/plugins/
unzip -o "/tmp/mountapp-${version}.zip" -d ~/.edm/plugins/
```
Grant execute permissions to extracted folder

```bash
chmod +x ~/.edm/plugins/mountapp/bin/DasfsWorker
chmod +x ~/.edm/plugins/mountapp/bin/dasd
chmod +x ~/.edm/plugins/mountapp/bin/*.sh
```

2 **Apple Silicon Special Settings**:

If current machine has Apple silicon processor (M1/M2/M3, etc.), additional Apple settings need to be modified to allow system extension loading.

Please refer to [Apple Official Documentation](https://support.apple.com/zh-cn/guide/mac-help/mchl768f7291/26/mac/26) to complete configuration.

3 **macFUSE Dependency Notes**:

⚠️ **Important**: macOS depends on macFUSE driver, which needs to be installed manually.

macFUSE is a FUSE (Filesystem in Userspace) implementation for macOS that allows users to run their own file systems without kernel support. When installing macFUSE, it needs to match the current operating system version, otherwise compatibility issues may occur. The correspondence is as follows:
Here is the macOS system version and recommended macFUSE driver version correspondence table:

| macOS Version | macFUSE Version | Notes |
|------------|--------------|------|
| Tahoe 26.x | 5.1.2 | If macOS system is the latest version, it is recommended to download and install the latest version of macFUSE. |
| Sequoia 15.x | 4.10.2 | |
| Sonoma 14.x | 4.6.1 | |
| Ventura 13.x | 4.6.1 | |
| Monterey 12.x | 4.6.1 | |
| Big Sur 11.x | 4.6.1 | |
| Other older versions | 3.11.2 | |

Based on current macOS version, guide users to complete installation.
- If not currently installed, guide users to download and install the corresponding version of macFUSE.
- If currently installed macFUSE version does not match system version, guide users to uninstall and install the corresponding version of macFUSE.

After macFUSE installation, if prompted **System Extension Blocked**, follow these steps:
- Click to open **Security & Privacy Preferences**, navigate to **System Settings > Privacy & Security**
- In **Security** area, select Allow apps downloaded from **App Store and identified developers**
- Authorize macFUSE (**Developer: Benjamin Fleischer**) to load.

After modifying above settings, you may need to restart the computer.


#### Linux Installation

1. **CentOS/RedHat (RPM systems)**:

```bash
# Directly install RPM package
sudo rpm -ivh /tmp/mountapp-${version}.rpm
```

2. **Ubuntu/Debian (DEB systems)**:

```bash
# Install conversion tool
sudo apt-get install -y alien

# Convert RPM to DEB
cd /tmp
sudo alien mountapp-${version}.rpm

# Install converted DEB package
sudo dpkg -i mountapp_${version}_*.deb
```

3. **Check FUSE2 Dependency**:

⚠️ **Important**: Linux systems require fuse2 version.

```bash
# Check if fuse2 is installed
dpkg -l | grep fuse  # Debian/Ubuntu
rpm -qa | grep fuse  # CentOS/RedHat

# If fuse2 is not installed, install it first
sudo apt-get install -y fuse  # Ubuntu/Debian (fuse2.9.9)
sudo yum install -y fuse      # CentOS/RedHat
```

**Notes**:
- Must install fuse2 (e.g., fuse2.9.9)
- If system has fuse3, no need to uninstall fuse3, you can directly install fuse2, both can coexist

---

### Step 5: Verify Installation

Verify installation results based on operating system:

#### Windows Verification

1. **Check if files exist**:

```powershell
# Check mountapp directory
Test-Path "$env:USERPROFILE\.edm\plugins\mountapp"
```

**Expected output**: `True`

2. **Check Dokan service status**:

```powershell
# Query Dokan service
sc query dokan1
```

**Expected output**: Should display service status (RUNNING or STOPPED)

#### macOS Verification

```bash
# Check mountapp directory
ls -la ~/.edm/plugins/mountapp
```

**Expected output**: Should display mountapp related files and directories

#### Linux Verification

```bash
# Check mountapp directory
ls -la /opt/mountapp
```

**Expected output**: Should display mountapp related files and directories

---

### Step 6: Start Software

**Pre-start check**: First check if mount app is already running. If running, skip this step and go directly to Step 7.

#### Check Method

- **Windows**: View Task Manager, check if `DasfsWorker` process is running
- **macOS**: Check if `DasfsWorker` process is running
- **Linux**: Use command `systemctl status mountapp` to check if mountapp service is running

#### Windows Start Mount App

If not running, use following steps to start:

1. **Get User ID**:

```powershell
$userIdJson = aliyun pds mountapp --action get-user-id --user-agent AlibabaCloud-Agent-Skills
$userId = ($userIdJson | ConvertFrom-Json).user_id
```

2. **Generate Random Port and Save**:

```powershell
# Randomly select a port from range 49152~65535
$port = Get-Random -Minimum 49152 -Maximum 65536

# Write to port file (no newline)
[System.IO.File]::WriteAllText("$env:USERPROFILE\.dasfs-worker-port", $port)
```

3. **Create startup script `start-task.ps1`**:

```powershell
$binDir = "$env:USERPROFILE\.edm\plugins\mountapp\bin"
$logDir = "$env:USERPROFILE\.pdsdrive\log"

# Ensure log directory exists
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

# Create startup script
$script = @"
`$logDir = `"$logDir`"
cd `"$binDir`"
.\start.bat $port $userId 2>&1 | Out-File -FilePath `"`$logDir\mountapp-task.log`" -Append
"@

$script | Out-File -FilePath "$binDir\start-task.ps1" -Encoding UTF8
```

4. **Register Windows Scheduled Task**:

```powershell
$taskName = "PDS MountApp Service"

# Define task action
$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$binDir\start-task.ps1`"" `
  -WorkingDirectory $binDir

# Define task principal (run as current user)
$principal = New-ScheduledTaskPrincipal `
  -UserId "$env:USERDOMAIN\$env:USERNAME" `
  -LogonType S4U `
  -RunLevel Limited

# Define trigger (at system startup)
$trigger = New-ScheduledTaskTrigger -AtStartup

# Define task settings (auto restart on failure)
$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -RestartCount 999 `
  -RestartInterval (New-TimeSpan -Minutes 1)

# Register scheduled task
Register-ScheduledTask `
  -TaskName $taskName `
  -Action $action `
  -Principal $principal `
  -Trigger $trigger `
  -Settings $settings `
  -Force

# Start task
Start-ScheduledTask -TaskName $taskName
```

5. **Verify Startup**:

Wait 5-10 seconds, then check process:

```powershell
Get-Process | Where-Object {$_.ProcessName -like "*DasfsWorker*"}
```

**Expected output**: Should display DasfsWorker process running

---

#### macOS Start Mount App

Use **launchd (plist)** method to start mount app, which is the most stable and reliable startup method on macOS.

1. **Get User ID and Generate Port**:

```bash
# Get user ID
user_id_json=$(aliyun pds mountapp --action get-user-id --user-agent AlibabaCloud-Agent-Skills)
user_id=$(echo "$user_id_json" | jq -r '.user_id')

# Generate random port
port=$((49152 + RANDOM % 16384))

# Write to port file (no newline)
echo -n $port > ~/.dasfs-worker-port
```

2. **Create plist file**:

Create `~/Library/LaunchAgents/com.aliyun.pds.mountapp.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Global unique identifier -->
    <key>Label</key>
    <string>com.aliyun.pds.mountapp</string>

    <!-- Use bash to execute DasfsWorker directly -->
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd $HOME/.edm/plugins/mountapp/bin &amp;&amp; ./DasfsWorker start --port=PORT_PLACEHOLDER --userId=USERID_PLACEHOLDER --dataPath=$HOME/.pdsdrive --logPath=$HOME/.pdsdrive/log</string>
    </array>

    <!-- Auto start when user logs in -->
    <key>RunAtLoad</key>
    <true/>

    <!-- Auto restart after process exits (only on non-successful exit or crash) -->
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>

    <!-- Working directory -->
    <key>WorkingDirectory</key>
    <string>$HOME/.edm/plugins/mountapp/bin</string>

    <!-- Environment variables -->
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>$HOME</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>

    <!-- Log output -->
    <key>StandardOutPath</key>
    <string>$HOME/.pdsdrive/log/mountapp.out.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.pdsdrive/log/mountapp.err.log</string>

    <!-- Startup interval: avoid frequent restarts after crash -->
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
```

**Note**: Placeholders in plist file need to be replaced:
- Replace `PORT_PLACEHOLDER` with actual port number
- Replace `USERID_PLACEHOLDER` with actual user ID
- Replace `$HOME` with current user's home directory path

3. **Load and Start launchd Service**:

```bash
# Ensure log directory exists
mkdir -p ~/.pdsdrive/log

# First time load and start
launchctl load ~/Library/LaunchAgents/com.aliyun.pds.mountapp.plist
sleep 2
launchctl start com.aliyun.pds.mountapp
sleep 3

# If already loaded, unload first then reload
# launchctl unload ~/Library/LaunchAgents/com.aliyun.pds.mountapp.plist 2>/dev/null
# sleep 1
# launchctl load ~/Library/LaunchAgents/com.aliyun.pds.mountapp.plist
# sleep 2
# launchctl start com.aliyun.pds.mountapp
```

4. **Verify Startup**:

Wait 3-5 seconds, then check if process started successfully:

```bash
ps aux | grep DasfsWorker | grep -v grep
```

**Expected output**: Should display DasfsWorker process running

**Note**: After using `launchctl unload` to stop service, it is recommended to wait 1-2 seconds before reloading to ensure process completely stops.

---

#### Linux Start Mount App

Linux starts automatically after installing rpm or deb package, no additional startup needed. The port number is already written to `~/.dasfs-worker-port` file.

If manual startup is needed:

```bash
# Start service
sudo systemctl start mountapp

# Set to start on boot
sudo systemctl enable mountapp

# View status
systemctl status mountapp
```

---

### Step 7: Check and Enable Mount App Feature

Before mounting, you need to enable mount app feature using command line:

```bash
aliyun pds mountapp --action enable-mountapp --user-agent AlibabaCloud-Agent-Skills
```

**Success output**:
```json
{"mount_app_enable": "success", "domain_id": "bj123"}
```


**Notes**:
1. If enabling fails, check:
   - Whether PDS drive DomainId, UserID, etc. are configured
   - Whether the configured account has permission to enable mount app feature
2. Enabling mount app only needs to be done once. If already enabled successfully, no need to repeat

---

### Step 8: Complete Mounting

#### 8.1 Query Mount App Status

Query mount app status before mounting. If already mounted, skip mounting step:

```bash
aliyun pds mountapp --action get-status --user-agent AlibabaCloud-Agent-Skills
```

**Example output**:
```json
{
    "UserId": "123456",
    "DomainId": "bj123",
    "Username": "root",
    "MountedStatus": "MountSuc",
    "Message": ""
}
```

**Status description**:
- `MountSuc`: Already mounted successfully, no need to mount again
- `Starting`: Mounting in progress, continue querying status. If not completed within 2 minutes, report mounting failure, need to remount
- `Init`: Not mounted, need to execute mounting operation

---

#### 8.2 Execute Mounting Operation

If status is `Init`, execute mounting:

```bash
# Basic mount command
aliyun pds mountapp --action mount --user-agent AlibabaCloud-Agent-Skills

# Linux non-root users need to specify mount-user
aliyun pds mountapp --action mount --mount-user admin --user-agent AlibabaCloud-Agent-Skills
```

**Note**: For Linux systems, check current running user. If not root user, add `--mount-user` parameter.

**Success output**:
```json
{"domain_id": "bj123", "user_id": "123456", "message": "mount success, please check status"}
```

---

#### 8.3 Verify Mount Status

After command execution succeeds, confirm mounting completion by querying status:

```bash
aliyun pds mountapp --action get-status --user-agent AlibabaCloud-Agent-Skills
```

**Expected output**:
```json
{
    "DomainId": "bj123",
    "Message": "",
    "MountedStatus": "MountSuc",
    "SubDomainId": "",
    "UserId": "123456",
    "Username": "user1"
}
```

If `MountedStatus` is `MountSuc`, mounting is successful!

---

#### 8.4 Query Mount Configuration

After successful mounting, you can query mount app configuration:

```bash
aliyun pds mountapp --action get-config --user-agent AlibabaCloud-Agent-Skills
```

**Example output**:
```json
{
   "DiskCachePath": "/Users/user1/.pdsdrive/cf8833674b2544b8aeeed2426bbdc4d9/cache",
   "DiskCacheSize": 5,
   "DomainId": "bj123",
   "Language": "zh",
   "MemoryCacheSize": 64,
   "MountPath": "/Users/user1/PDSDrive",
   "MountUser": "",
   "ShowIconPreview": true,
   "SubDomainId": "",
   "UserId": "cf8833674b2544b8aeeed2426bbdc4d9",
   "Version": "0.8.2"
}
```

**Important**: The `MountPath` field is the mount point path where mounting succeeded. Users can access this path to view mounted files.

---

#### 8.5 About Boot Startup and Exception Handling

1. **Not mounted after boot startup**: If after boot startup, query status shows not mounted (`Init`), need to execute mounting using command `aliyun pds mountapp --action mount --user-agent AlibabaCloud-Agent-Skills`

2. **After process abnormal restart**: If process has exception and restarts, query status shows not mounted (`Init`), need to execute mounting using command `aliyun pds mountapp --action mount --user-agent AlibabaCloud-Agent-Skills`

---

### Step 9: Modify Mount App Configuration
Currently supports modifying mount app language. The command:
```bash
aliyun pds mountapp --action set-config --language zh --user-agent AlibabaCloud-Agent-Skills
```
Currently supports three languages:
- `zh`: Chinese
- `en`: English
- `es`: Spanish

**Note**: Changing mount language requires remounting to take effect

---

## Success Verification

### Verify Mount Point is Accessible

Access mount point based on operating system:

**Windows**:
```powershell
# Default mount point: P:\
dir P:\
```

**macOS/Linux**:
```bash
# Default mount point: ~/PDSDrive
ls -la ~/PDSDrive
```

**Expected output**:
```
Personal Space
Team Space
Received Shares
```
Expect at least one of the above three directories to exist

### Mount App Directory Structure

After successful mounting, top-level directory is read-only, with some system-level directories:

```bash
tree -L 1 ~/PDSDrive/
~/PDSDrive/
├── Personal Space
├── Team Space
└── Received Shares
```

**Directory description**:
- **Personal Space**: This directory allows direct read/write
- **Team Space**: This directory is read-only, lists team spaces with permissions. After entering team space, may be read-only or read-write depending on granted permissions
- **Received Shares**: This directory is read-only, lists shares with permissions. After entering share directory, may be read-only or read-write depending on granted permissions

### Access Files

**Windows**:
```powershell
# Access Personal Space
dir "P:\Personal Space"
```

**macOS/Linux**:
```bash
# Access Personal Space
ls -la ~/PDSDrive/Personal\ Space
```

---

## Stop and Uninstall

**Important**: Stopping and uninstalling mount app are **high-risk operations**. Before operation, human confirmation is required: Please confirm all files opened under mount drive letter (such as P:\ on Windows) or mount directory (~/PDSDrive on macOS and Linux) have been saved and closed to avoid data loss. Only proceed with subsequent operations after human confirmation.

### How to Stop Mount App

#### Windows

```powershell
cd $env:USERPROFILE\.edm\plugins\mountapp\bin
.\stop.bat
```

Stop and unregister Windows scheduled task

```powershell
Stop-ScheduledTask -TaskName "PDS MountApp Service" -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "PDS MountApp Service" -Confirm:$false
```

#### macOS

```bash
# Use launchctl to stop service
launchctl stop com.aliyun.pds.mountapp
launchctl unload ~/Library/LaunchAgents/com.aliyun.pds.mountapp.plist

# Or use stop.sh script
cd ~/.edm/plugins/mountapp/bin
bash stop.sh
```

#### Linux

```bash
sudo systemctl stop mountapp
```

---

### How to Uninstall Mount App Plugin

⚠️ **Important**: Must stop mount app service before uninstalling

#### Windows

1. **Stop service**:
```powershell
cd $env:USERPROFILE\.edm\plugins\mountapp\bin
.\stop.bat
```

2. **Delete scheduled task**:
```powershell
Unregister-ScheduledTask -TaskName "PDS MountApp Service" -Confirm:$false
```

3. **Delete plugin files**:
```powershell
Remove-Item -Path "$env:USERPROFILE\.edm\plugins\mountapp" -Recurse -Force
```

#### macOS

1. **Stop service**:
```bash
launchctl stop com.aliyun.pds.mountapp
launchctl unload ~/Library/LaunchAgents/com.aliyun.pds.mountapp.plist
rm ~/Library/LaunchAgents/com.aliyun.pds.mountapp.plist
```

2. **Delete plugin files**:
```bash
rm -rf ~/.edm/plugins/mountapp
```

#### Linux

1. **Stop service**:
```bash
sudo systemctl stop mountapp
sudo systemctl disable mountapp
```

2. **Uninstall software package**:

**RPM systems (CentOS/RedHat)**:
```bash
sudo rpm -e mountapp
```

**DEB systems (Ubuntu/Debian)**:
```bash
sudo apt-get remove mountapp
```

---

## Default Mount Points

Default mount points for different operating systems:

| Operating System | Default Mount Point |
|---------|-----------||
| **Windows** | `P:\` |
| **macOS** | `~/PDSDrive` |
| **Linux** | `~/PDSDrive` |

---

## Usage Limitations

Mount app maps cloud drive storage to local file system, enabling access to PDS cloud drive files like local files. However, there are some limitations:

1. **File type limitations**:
   - ✅ Supports upload/download of various file types
   - ✅ Supports access to various documents, images, videos, etc.
   - ❌ Does not support read/write of certain special files, such as: database files, git code repositories, svn, encrypted files, etc.

2. **Collaboration limitations**:
   - ❌ Does not support simultaneous multi-user editing (collaboration)
   - For multi-user collaborative editing, please use PDS cloud drive's online editing feature

3. **Platform limitations**:
   - ❌ Does not support installation on Windows systems with ARM processors (e.g., some Microsoft Surface devices using Qualcomm Snapdragon processors)

4. **Performance limitations**:
   - When simultaneously transferring more than 1000 files, may require longer time
   - When single file size exceeds 1GB, may require longer time
   - Recommendation: For large numbers of files or large file transfers, use enterprise cloud drive desktop client for best performance

5. **Network requirements**:
   - Mount app has certain requirements for network bandwidth and stability
   - When network bandwidth is low or network is unstable (e.g., mobile hotspot, restricted network environment), file upload/download may fail
   - Recommendation: When network is poor, use sync backup or enterprise cloud drive desktop client

6. **Windows 7 compatibility**:
   - ⚠️ Since Microsoft terminated Windows 7 support on January 14, 2020, some Windows 7 systems may not be able to use mount app
   - Recommendation: Upgrade system to Windows 10 or Windows 11

---

## Error Handling

### Common Error Scenarios

| Error Type | Solution |
|---------|---------||
| **Download failed** | Check network connection, retry or use mirror source |
| **Verification failed** | Re-download, confirm file integrity |
| **Installation failed** | Check permissions, confirm dependencies are met |
| **Version conflict** | Prompt user to choose version or uninstall old version |
| **Startup failed** | Check if port is occupied, check for process conflicts |
| **Mount failed** | Check if service is running, check if driver is installed, view log files |

### Log File Locations

**Windows**:
```
%USERPROFILE%\.pdsdrive\log\mountapp-task.log
```

**macOS**:
```
~/.pdsdrive/log/mountapp.out.log
~/.pdsdrive/log/mountapp.err.log
```

**Linux**:
```bash
journalctl -u mountapp -n 50
```


---

## Best Practices

1. ✅ **Always complete preparation before installation**
2. ✅ **Configure PDS-specific config (domain_id, user_id, authentication-type)**
3. ✅ **Check if already installed and version before installation**
4. ✅ **Verify driver/service is running**
5. ✅ **Windows uses scheduled tasks for boot startup**
6. ✅ **macOS uses launchd (plist) for stable startup**
7. ✅ **Linux ensure fuse2 dependency is installed**
8. ✅ **Set timeout when handling "Starting" mount status**
9. ✅ **Query actual mount path (do not assume default path)**
10. ✅ **Stop service before cleanup/uninstall**

---

## Task Progress Tracking

Use the following checklist to track mount app installation progress:

```
Mount app download, install, and startup progress:
- [ ] Step 1: Check if mount app is installed and current version
- [ ] Step 2: Get mount app plugin latest version and download URL
- [ ] Step 3: Download installation package (if update or first install needed)
- [ ] Step 4: Execute installation (extract/driver install/dependency install)
- [ ] Step 5: Verify installation results
- [ ] Step 6: Start mount app (check process/register boot startup)
- [ ] Step 7: Check and enable mount app feature (enable-mountapp)
- [ ] Step 8: Complete mounting (query status and execute mount command)
```

---

## Reference Resources

### PDS CLI Plugin Extended Commands for Mount App (mountapp) Feature:

| CLI Command | Description | Usage Scenario |
|-------------|----------------|-------||
| `aliyun pds mountapp --action get-latest-version` | Get mount app latest version and download URL | Used in Step 2 for checking updates |
| `aliyun pds mountapp --action get-user-id` | Get current user ID | Used in Step 6 to get user ID required for startup |
| `aliyun pds mountapp --action enable-mountapp` | Enable mount app feature for cloud drive | Used in Step 7 to enable mount app feature |
| `aliyun pds mountapp --action mount` | Execute mount operation | Used in Step 8 to mount cloud drive |
| `aliyun pds mountapp --action get-status` | Query mount app status | Used in Step 8 to check mount status |
| `aliyun pds mountapp --action get-config` | Query mount app configuration | Used to view current mount settings and mount point |
| `aliyun pds mountapp --action update-config` | Update mount app configuration | Used to modify mount settings |

**Note**: All `aliyun pds mountapp` commands must include `--user-agent AlibabaCloud-Agent-Skills` flag.

### 

### Official Documentation
- **PDS Cloud Drive Mount App Plugin**: https://help.aliyun.com/zh/pds/drive-and-photo-service-ent/user-guide/mount-drives?spm=a2c4g.750001.0.i2
- **Aliyun CLI Documentation**: https://help.aliyun.com/zh/cli/



