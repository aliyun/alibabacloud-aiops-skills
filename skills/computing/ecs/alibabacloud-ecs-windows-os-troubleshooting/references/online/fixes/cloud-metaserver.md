# Cloud MetaServer Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Firewall blocking metadata service

**Fix operation**:

```powershell
# Disable firewall rules blocking 100.100.100.200 (replace with actual rule name)
# Confirm the rule name before executing the following command
Get-NetFirewallRule -Enabled True -Action Block | ForEach-Object {
    $addrFilter = Get-NetFirewallAddressFilter -AssociatedNetFirewallRule $_ -ErrorAction SilentlyContinue
    if ($addrFilter.RemoteAddress -match '100\.100\.100\.200') {
        Write-Host "Disabling rule: $($_.DisplayName)"
        Disable-NetFirewallRule -Name $_.Name
    }
}
```

**Verification**:

```powershell
Test-NetConnection -ComputerName 100.100.100.200 -Port 80 -WarningAction SilentlyContinue | Select-Object TcpTestSucceeded
```

Expected result: TcpTestSucceeded is True

**Risk notes**:

- **Session impact**: Disabling rules takes effect immediately and does not affect RDP connections.
- **Persistence scope**: Firewall rule changes are retained after reboot.
- **Rollback command**: `Enable-NetFirewallRule -DisplayName '<RuleName>'`
- **Note**: Please confirm that this rule is an erroneously added blocking rule rather than an intentional one.

### Root cause: Metadata service unreachable

**Fix operation**:

```powershell
# Check metadata service route
$route = Get-NetRoute -DestinationPrefix "100.100.100.200/32" -ErrorAction SilentlyContinue
if ($route) {
    $route | Select-Object DestinationPrefix, NextHop | Format-Table -AutoSize
    Write-Host "Route to metadata service exists"
} else {
    Write-Host "Route to metadata service is missing"
}

# If route is missing, add route to metadata service via default gateway
$gateway = (Get-NetRoute -DestinationPrefix 0.0.0.0/0 -ErrorAction SilentlyContinue | Select-Object -First 1).NextHop
if ($gateway) {
    New-NetRoute -DestinationPrefix "100.100.100.200/32" -NextHop $gateway -PolicyStore ActiveStore -ErrorAction SilentlyContinue | Out-Null
    Write-Host "Route added: 100.100.100.200/32 via $gateway"
}
```

**Verification**:

```powershell
Invoke-WebRequest -Uri "http://100.100.100.200/latest/meta-data/instance-id" -TimeoutSec 5 -UseBasicParsing
```

Expected result: Returns instance ID (e.g. i-bp1234567890abcdef)

**Risk notes**:

- **Session impact**: Adding a route takes effect immediately and does not affect existing connections.
- **Persistence scope**: Temporary operation (PolicyStore=ActiveStore), invalid after reboot. To make it permanent, add it to a startup script.
- **Rollback command**: `Remove-NetRoute -DestinationPrefix '100.100.100.200/32' -Confirm:$false`

### Root cause: Metadata hardening mode or access control blocking

**Fix operation**: Hardening mode is an expected security behavior; there is no fix action within the OS, and bypass attempts should not be made. Handle as follows:

1. Confirm with the user whether the instance intentionally enabled metadata hardening mode / access control policy; if intentional, inform that functions relying on metadata (NTP/KMS/WSUS assignment, etc.) being restricted is expected behavior
2. If normal access needs to be restored: the user should adjust the instance metadata access configuration in the ECS console (disable hardening mode or allow access control); there is no corresponding command within the OS
3. If the business must read metadata in hardening mode: access via the platform-specified method (e.g. with required request headers or credentials), and the user should modify business code accordingly

**Verification**:

```powershell
# Re-test metadata access after user adjusts console settings
Invoke-WebRequest -Uri "http://100.100.100.200/latest/meta-data/instance-id" -TimeoutSec 5 -UseBasicParsing
```

Expected result: Returns 200 with instance ID as content (if hardening mode is maintained, 403 is expected)

**Risk notes**:

- **Session impact**: None, console configuration changes do not disconnect existing connections.
- **Persistence scope**: Console configuration is retained after reboot.
- **Rollback command**: Re-enable hardening mode in the console to restore the original state.
- **Note**: Do not bypass hardening mode by modifying routes/firewall/proxy, as this will break the user's security expectations.

### Root cause: NTP server not assigned

**Fix operation**:

```powershell
# Configure Alibaba Cloud NTP server
w32tm /config /manualpeerlist:"ntp.cloud.aliyuncs.com" /syncfromflags:manual /reliable:yes /update

# Restart time service
Restart-Service W32Time

# Force sync
w32tm /resync
```

**Verification**:

```powershell
w32tm /query /status
```

Expected result: Source shows ntp.cloud.aliyuncs.com, Last Successful Sync Time is recent

**Risk notes**:

- **Session impact**: Modifying NTP configuration will immediately trigger time synchronization. If the current time deviation is large, the jump may affect applications that rely on timestamps.
- **Persistence scope**: W32Time configuration is written to the registry and retained after reboot.
- **Rollback command**: `w32tm /config /manualpeerlist:"<OriginalNTPServer>" /syncfromflags:manual /update`

### Root cause: KMS activation server unreachable

**Fix operation**:

```powershell
# Configure KMS server
cscript //Nologo C:\windows\system32\slmgr.vbs /skms kms.cloud.aliyuncs.com:1688

# Try to activate
cscript //Nologo C:\windows\system32\slmgr.vbs /ato
```

**Verification**:

```powershell
cscript //Nologo C:\windows\system32\slmgr.vbs /dlv
```

Expected result: License Status shows Licensed

**Risk notes**:

- **Session impact**: None, activation does not affect existing connections.
- **Persistence scope**: Activation state is persistent.
- **Rollback command**: No rollback needed (activation failure does not change existing state).
- **Note**: If the KMS server is still unreachable, activation will fail. Ensure network connectivity first.

### Root cause: WSUS update server unreachable

**Fix operation**:

```powershell
# Option 1: Remove WSUS configuration, revert to Microsoft Update
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" -Name WUServer -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" -Name WUStatusServer -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" -Name UseWUServer -ErrorAction SilentlyContinue
Restart-Service wuauserv
```

**Verification**:

```powershell
# Check Windows Update service status
Get-Service wuauserv | Select-Object Name, Status | Format-Table -AutoSize

# Manually trigger update check
(New-Object -ComObject Microsoft.Update.AutoUpdate).DetectNow()
```

Expected result: wuauserv service is running, update check no longer reports errors

**Risk notes**:

- **Session impact**: Restarting wuauserv does not affect existing RDP connections.
- **Persistence scope**: Registry changes are retained after reboot. If deployed via group policy, it will be overwritten on the next GPO refresh.
- **Rollback command**: Reconfigure WSUS server address (`Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate' -Name 'WUServer' -Value '<WSUS_URL>'`).
- **Note**: After clearing WSUS configuration, the system will directly obtain updates from Microsoft Update online. If the network environment restricts external access, WSUS configuration should be retained.

### Root cause: Hostname mismatch

**Fix operation**:

```powershell
# Option 1: Rename system hostname to match metadata (replace with actual metadata hostname)
# Rename-Computer -NewName "<hostname-from-metadata>" -Restart -Force

# Option 2: Modify instance hostname via ECS console to match system hostname (requires cloud console operation)
```

**Verification**:

```powershell
$osName = (Get-CimInstance Win32_OperatingSystem).CSName
$metaName = (Invoke-WebRequest -Uri "http://100.100.100.200/latest/meta-data/hostname" -TimeoutSec 5 -UseBasicParsing).Content
[PSCustomObject]@{ SystemHostname=$osName; MetadataHostname=$metaName; Match=($osName -eq $metaName) } | Format-List
```

Expected result: Match is True

**Risk notes**:

- **Session impact**: Rename-Computer requires a system reboot to take effect, which will interrupt all current connections and services.
- **Persistence scope**: Takes effect after reboot, permanent change.
- **Rollback command**: `Rename-Computer -NewName '<OriginalHostname>' -Restart -Force`
- **Note**: If the server is domain-joined, modifying the hostname requires domain administrator privileges and may affect domain services.
