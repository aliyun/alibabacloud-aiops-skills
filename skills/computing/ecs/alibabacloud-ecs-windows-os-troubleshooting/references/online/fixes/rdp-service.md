# RDP Service Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: TermService service stopped / disabled

**Fix operation**:

```powershell
# Start dependent services
Get-Service -Name TermService -RequiredServices | ForEach-Object {
    if ($_.Status -ne 'Running') {
        Start-Service -Name $_.Name -ErrorAction SilentlyContinue
        Write-Host "Started dependent service: $($_.Name)"
    }
}

# Enable and start TermService
Set-Service -Name TermService -StartupType Automatic
Start-Service -Name TermService
Write-Host "Started TermService"
```

**Verification**:

```powershell
Get-Service -Name TermService | Select-Object Name, Status, StartType | Format-Table -AutoSize
Get-NetTCPConnection -LocalPort 3389 -State Listen -ErrorAction SilentlyContinue | Format-Table -AutoSize
```

Expected result: TermService Status = Running, StartType = Automatic, port 3389 is in Listen state

**Risk notes**:

- **Session impact**: None; starting the service does not interrupt existing connections.
- **Persistence scope**: StartupType change persists across reboots.
- **Rollback command**: `Stop-Service TermService; Set-Service -Name TermService -StartupType Disabled`
- **Note**: Enabling TermService turns on Remote Desktop functionality; ensure strong passwords are configured.

---

### Root cause: TermService dependent service abnormal

**Fix operation**:

```powershell
# Start all dependent services of TermService (replace <ServiceName> with actual dependent service name)
Start-Service -Name "<ServiceName>"

# Start TermService
Start-Service -Name TermService
```

**Verification**:

```powershell
Get-Service -Name TermService -RequiredServices | Select-Object Name, Status, StartType | Format-Table -AutoSize
```

Expected result: All dependent services Status = Running

**Risk notes**:

- **Session impact**: None; starting dependent services does not interrupt existing connections.
- **Persistence scope**: Starting a service is a temporary operation; if combined with StartupType modification, it persists across reboots.
- **Rollback command**: `Stop-Service -Name '<ServiceName>'`
- **Note**: Dependent services may have their own dependencies and need to be started in order.

---

### Root cause: RDP listener configuration lost

**Fix operation**:

```powershell
# Recreate RDP-Tcp listener registry key
New-Item -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" -Force

# Set default port
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" -Name "PortNumber" -Value 3389

# Restart TermService
Restart-Service -Name TermService -Force
```

**Verification**:

```powershell
Get-ChildItem -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations" |
    Where-Object { $_.PSChildName -ne "Console" } |
    ForEach-Object { [PSCustomObject]@{ Station = $_.PSChildName; PortNumber = (Get-ItemProperty $_.PSPath).PortNumber } }
```

Expected result: At least RDP-Tcp exists, PortNumber = 3389

**Risk notes**:

- **Session impact**: Recreating the listener configuration will interrupt existing RDP connections.
- **Persistence scope**: Registry modifications persist across reboots.
- **Rollback command**: `Remove-Item -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Recurse -Force` (restore to pre-fix state).

---

### Root cause: RDP listener disabled or enable flag not configured (fEnableWinStation)

**Fix operation**:

```powershell
# View current fEnableWinStation value (replace <StationName> with actual station name)
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>" -Name fEnableWinStation -ErrorAction SilentlyContinue

# Enable the WinStation
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>" -Name "fEnableWinStation" -Value 1

# Restart TermService to apply
Restart-Service -Name TermService -Force
```

**Verification**:

```powershell
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>" -Name fEnableWinStation
qwinsta | Select-String -Pattern "rdp-tcp"
```

Expected result: fEnableWinStation = 1, rdp-tcp session State = Listen

**Risk notes**:

- **Session impact**: Restarting TermService will briefly interrupt existing RDP connections.
- **Persistence scope**: Registry modifications persist across reboots.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>' -Name 'fEnableWinStation' -Value 0`
- **Note**: Do NOT blindly enable third-party WinStations; a third-party Station enabled alongside RDP-Tcp may seize the listening port and cause mstsc session initialization failure and immediate disconnect. Only enable the station intended for standard RDP use (usually RDP-Tcp).

---

### Root cause: RDP listening port changed to non-standard port

**Fix operation**:

```powershell
# Change RDP port back to default 3389 for specified WinStation (replace <StationName> with actual station name)
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>" -Name "PortNumber" -Value 3389

# Restart TermService
Restart-Service -Name TermService -Force

# Add firewall rule
New-NetFirewallRule -DisplayName "Allow RDP" -Direction Inbound -Protocol TCP -LocalPort 3389 -Action Allow -Profile Any
```

**Verification**:

```powershell
Get-ChildItem -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations" |
    Where-Object { $_.PSChildName -ne "Console" } |
    ForEach-Object { [PSCustomObject]@{ Station = $_.PSChildName; PortNumber = (Get-ItemProperty $_.PSPath).PortNumber } }
Get-NetTCPConnection -LocalPort 3389 -State Listen
```

Expected result: Target WinStation PortNumber = 3389, port is in listening state

**Risk notes**:

- **Session impact**: Changing the port will interrupt existing RDP connections.
- **Persistence scope**: Registry modifications persist across reboots.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>' -Name 'PortNumber' -Value <OriginalPort>`
- **Note**: If using a non-standard port connection method, the client configuration must be updated accordingly.

---

### Root cause: RDP listener not running

**Fix operation**:

```powershell
# Check current session status
qwinsta

# Restart TermService to restore listener
Restart-Service -Name TermService -Force

# If still no listener, check underlying causes (port conflict, service errors, etc.)
Get-Service -Name TermService | Select-Object Name, Status, StartType | Format-Table -AutoSize
```

**Verification**:

```powershell
qwinsta | Select-String -Pattern "Listen"
```

Expected result: rdp-tcp session exists, State = Listen

**Risk notes**:

- **Session impact**: Restarting TermService will briefly interrupt existing RDP connections.
- **Persistence scope**: Service restart is a temporary operation.
- **Rollback command**: No rollback needed (restarting the service is a diagnostic operation).
- **Note**: If there is still no Listen session after restart, investigate underlying causes such as port conflicts or WinStation being disabled.

---

### Root cause: Third-party remote component

**Fix operation**:

```powershell
# List all WinStations and their WdName
Get-ChildItem -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations" |
    Where-Object { $_.PSChildName -ne "Console" } | ForEach-Object {
        [PSCustomObject]@{
            StationName = $_.PSChildName
            WdName = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).WdName
        }
    } | Format-Table -AutoSize

# If third-party Station causes conflict, disable that Station
# Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>" -Name "fEnableWinStation" -Value 0
```

**Verification**:

```powershell
# Confirm standard RDP-Tcp listener is normal
qwinsta | Select-String -Pattern "rdp-tcp"
```

Expected result: rdp-tcp session State = Listen, third-party Station disabled or uninstalled

**Risk notes**:

- **Session impact**: Disabling a third-party Station does not affect standard RDP connections.
- **Persistence scope**: Registry modifications persist across reboots.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>' -Name 'fEnableWinStation' -Value 1`
- **Note**: Before disabling, confirm the purpose of the third-party software; it may affect remote connections relying on that protocol.

---

### Root cause: Concurrent connection limit (MaxInstanceCount)

**Fix operation**:

```powershell
# View current MaxInstanceCount value (replace <StationName> with actual station name)
(Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>" -ErrorAction SilentlyContinue).MaxInstanceCount

# Remove restriction (set to unlimited)
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>" -Name "MaxInstanceCount" -Value 0xFFFFFFFF

# Restart TermService
Restart-Service -Name TermService -Force
```

**Verification**:

```powershell
(Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>").MaxInstanceCount
```

Expected result: MaxInstanceCount = 4294967295 (0xFFFFFFFF, unlimited)

**Risk notes**:

- **Session impact**: Restarting TermService will briefly interrupt existing RDP connections.
- **Persistence scope**: Registry modifications persist across reboots. If Group Policy sets MaxInstanceCount, it must be modified as well.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>' -Name 'MaxInstanceCount' -Value <OriginalValue>`
- **Note**: Increasing the concurrent connection count will consume more system resources.

---

### Root cause: WinStation registry read permission abnormal

**Fix operation**:

```powershell
# Add WinStations registry read permission for BUILTIN\Users
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations"
$acl = Get-Acl -Path $regPath
$rule = New-Object System.Security.AccessControl.RegistryAccessRule("BUILTIN\Users", "ReadKey", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.AddAccessRule($rule)
Set-Acl -Path $regPath -AclObject $acl
Write-Host "Added WinStations registry read permission for BUILTIN\Users"
```

**Verification**:

```powershell
(Get-Acl -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations").Access |
    Where-Object { $_.IdentityReference -match 'BUILTIN\\Users' } |
    Select-Object IdentityReference, RegistryRights, AccessControlType
```

Expected result: BUILTIN\Users has ReadKey permission, AccessControlType = Allow

**Risk notes**:

- **Session impact**: None; only adding registry permissions.
- **Persistence scope**: Permission modifications persist across reboots. If controlled by domain policy, it may be overwritten at the next GPO refresh.
- **Rollback command**: Manually remove the added ACL rule.

---

### Root cause: RDP port occupied by another process

**Fix operation**:

```powershell
# Find process occupying port 3389
$processId = (Get-NetTCPConnection -LocalPort 3389 -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
if ($processId) {
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    Write-Host "Process occupying port 3389: $($process.Name) (PID: $processId)"

    # Prompt user to confirm whether to terminate the process
    Write-Host "Recommended to terminate the process or change RDP port"
}
```

**Verification**:

```powershell
Get-NetTCPConnection -LocalPort 3389 -ErrorAction SilentlyContinue
```

Expected result: No other process occupying port 3389

**Risk notes**:

- **Session impact**: Terminating the process occupying the port may affect related system functionality.
- **Persistence scope**: Terminating a process is a temporary operation; it may restart after reboot.
- **Rollback command**: Restart the terminated process.
- **Note**: Terminating other processes may affect system functionality; proceed with caution.

---

### Root cause: Remote Desktop disabled (via registry)

**Fix operation**:

```powershell
# Enable Remote Desktop
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0
Write-Host "Remote Desktop enabled"
```

**Verification**:

```powershell
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections"
```

Expected result: fDenyTSConnections = 0

**Risk notes**:

- **Session impact**: None; only modifying registry configuration.
- **Persistence scope**: Registry modifications persist across reboots.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server' -Name 'fDenyTSConnections' -Value 1`
- **Note**: Enabling RDP increases the system attack surface; ensure strong passwords and firewall rules are configured.

---

### Root cause: Group Policy denies Remote Desktop connections / Group Policy overrides local configuration

**Fix operation**:

```powershell
# Modify Group Policy configuration
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services" -Name "fDenyTSConnections" -Value 0 -ErrorAction SilentlyContinue

# Also modify local configuration
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0

# Update Group Policy
gpupdate /force
```

**Verification**:

```powershell
Get-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services" -Name "fDenyTSConnections" -ErrorAction SilentlyContinue | Select-Object fDenyTSConnections
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" | Select-Object fDenyTSConnections
```

Expected result: Both fDenyTSConnections values are 0

**Risk notes**:

- **Session impact**: None; only modifying registry and policy configuration.
- **Persistence scope**: Local modifications persist across reboots. If the server is domain-managed, Group Policy may be overridden by the domain controller.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' -Name 'fDenyTSConnections' -Value 1`

---

### Root cause: Group Policy overrides RDP security configuration

**Fix operation**:

```powershell
# View current Group Policy overrides for RDP security configuration
$gpPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services"
Get-ItemProperty -Path $gpPath -Name SecurityLayer, UserAuthentication, MaxInstanceCount -ErrorAction SilentlyContinue | Select-Object SecurityLayer, UserAuthentication, MaxInstanceCount | Format-List

# Remove unnecessary Group Policy override values (replace <PolicyName> with actual policy name)
# Remove-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services" -Name "<PolicyName>" -ErrorAction SilentlyContinue

# Update Group Policy
gpupdate /force

# Restart TermService
Restart-Service -Name TermService -Force
```

**Verification**:

```powershell
$gpPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services"
Get-ItemProperty -Path $gpPath -Name SecurityLayer, UserAuthentication, MaxInstanceCount -ErrorAction SilentlyContinue | Select-Object SecurityLayer, UserAuthentication, MaxInstanceCount | Format-List
```

Expected result: Corresponding policy values have been removed (Value is empty) or modified to expected values

**Risk notes**:

- **Session impact**: Restarting TermService will briefly interrupt existing RDP connections.
- **Persistence scope**: Local modifications persist across reboots. If the server is joined to a domain, it may be overwritten by domain controller policy at the next gpupdate.
- **Rollback command**: Restore original policy values (e.g., `Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' -Name '<PolicyName>' -Value <OriginalValue>`).
- **Note**: Contact the domain administrator to modify in GPMC to ensure persistent effect.

---

### Root cause: Third-party WinStation conflicts with RDP-Tcp causing crash

**Fix operation**:

```powershell
# List all WinStations and identify port conflicts
$winStationsPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations"
$stations = Get-ChildItem -Path $winStationsPath | Where-Object { $_.PSChildName -ne "Console" }
$stations | ForEach-Object {
    $props = Get-ItemProperty -Path $_.PSPath -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        StationName       = $_.PSChildName
        PortNumber        = $props.PortNumber
        WdName            = $props.WdName
        fEnableWinStation = $props.fEnableWinStation
    }
} | Format-Table -AutoSize

# Disable conflicting third-party WinStation (replace <ThirdPartyStationName> with actual name)
# Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<ThirdPartyStationName>" -Name "fEnableWinStation" -Value 0

# If RDP-Tcp WdName was overwritten, restore to standard value
# Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" -Name "WdName" -Value "RDPWD"

# Restart TermService to apply changes
# Restart-Service -Name TermService -Force
```

**Verification**:

```powershell
qwinsta
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" | Select-Object WdName, PortNumber, fEnableWinStation
```

Expected result: rdp-tcp State = Listen, WdName = RDPWD, third-party WinStation disabled or uninstalled, mstsc connection no longer crashes

**Risk notes**:

- **Session impact**: Disabling third-party WinStation does not affect standard RDP connections; restarting TermService will briefly interrupt existing sessions.
- **Persistence scope**: Registry modifications persist across reboots.
- **Rollback command**: Restore WdName (`Set-ItemProperty ... -Name 'WdName' -Value '<OriginalValue>'`) or re-enable the third-party WinStation.
- **Note**: Before executing, ensure an alternative access channel is available via VNC or other console.

---

### Root cause: Multiple WinStations configured with the same port

**Fix operation**:

```powershell
# Identify duplicate port WinStations
$winStationsPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations"
$stations = Get-ChildItem -Path $winStationsPath | Where-Object { $_.PSChildName -ne "Console" }
$portMap = @{}
$stations | ForEach-Object {
    $props = Get-ItemProperty -Path $_.PSPath -ErrorAction SilentlyContinue
    $port = $props.PortNumber
    if (-not $portMap[$port]) { $portMap[$port] = @() }
    $portMap[$port] += $_.PSChildName
}

# Display conflicting stations
$portMap.GetEnumerator() | Where-Object { $_.Value.Count -gt 1 } | ForEach-Object {
    Write-Host "Port $($_.Key) is configured on multiple WinStations: $($_.Value -join ', ')"
}

# Fix: Keep primary WinStation (RDP-Tcp), disable or change port of redundant station
# Option A: Disable redundant WinStation
# Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<RedundantStationName>" -Name "fEnableWinStation" -Value 0

# Option B: Change redundant WinStation to a different port (e.g., 3390)
# Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<RedundantStationName>" -Name "PortNumber" -Value 3390
# New-NetFirewallRule -DisplayName "Allow RDP 3390" -Direction Inbound -Protocol TCP -LocalPort 3390 -Action Allow -Profile Any

# Restart TermService to apply changes
# Restart-Service -Name TermService -Force
```

**Verification**:

```powershell
$winStationsPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations"
Get-ChildItem -Path $winStationsPath | Where-Object { $_.PSChildName -ne "Console" } | ForEach-Object {
    $props = Get-ItemProperty -Path $_.PSPath -ErrorAction SilentlyContinue
    [PSCustomObject]@{ Station = $_.PSChildName; Port = $props.PortNumber; Enabled = $props.fEnableWinStation }
} | Format-Table -AutoSize
Get-NetTCPConnection -LocalPort 3389 -State Listen -ErrorAction SilentlyContinue | Format-Table -AutoSize
```

Expected result: Each enabled WinStation is configured with a different port, no port conflict; or redundant WinStation is disabled

**Risk notes**:

- **Session impact**: Disabling a WinStation will disconnect existing sessions on that listener; changing the port requires restarting TermService.
- **Persistence scope**: Registry modifications persist across reboots.
- **Rollback command**: `Set-ItemProperty ... -Name 'fEnableWinStation' -Value 1` (re-enable) or restore the original port number.
- **Note**: Changing the port requires adding firewall rules and notifying clients to use the new port.

---

### Root cause: UMBus device enumeration abnormal

**Fix operation**:

```powershell
# Rescan plug and play devices
pnputil /scan-devices

# Check UMBus device status
Get-PnpDevice -Class 'System' -ErrorAction SilentlyContinue | Where-Object {$_.FriendlyName -like '*UMBus*'} | Select-Object FriendlyName, Status | Format-Table -AutoSize
```

**Verification**:

```powershell
Get-PnpDevice -Class 'System' -ErrorAction SilentlyContinue | Where-Object {$_.FriendlyName -like '*UMBus*'} | Select-Object FriendlyName, Status | Format-Table -AutoSize
```

Expected result: All UMBus devices Status = OK

**Risk notes**:

- **Session impact**: None; only rescanning devices.
- **Persistence scope**: Device scan is a temporary operation.
- **Rollback command**: No rollback needed.
- **Note**: If the device is still abnormal, it may be necessary to update or reinstall the driver.
