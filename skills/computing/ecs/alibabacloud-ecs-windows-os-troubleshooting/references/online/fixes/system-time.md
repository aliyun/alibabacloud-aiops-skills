# System Time Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Time Zone Configuration Error

**Fix Action**:

```powershell
# Set time zone to China Standard Time
Set-TimeZone -Id 'China Standard Time'
```

**Verification**:

```powershell
Get-TimeZone | Select-Object Id, DisplayName, BaseUtcOffset | Format-Table -AutoSize
```

Expected result: Id = China Standard Time, BaseUtcOffset = 08:00:00

**Risk notes**:

- **Session impact**: None; time zone modification takes effect immediately but does not affect UTC time.
- **Persistence scope**: Time zone configuration takes effect permanently, retained after reboot.
- **Rollback command**: `Set-TimeZone -Id '<OriginalTimeZoneId>'`
- **Note**: Modifying the time zone will immediately affect the display of system time but will not affect UTC time; time-based decisions in running scheduled tasks may be affected.

---

### Root cause: RealTimeIsUniversal Configuration Error

**Fix Action**:

```powershell
# Set RealTimeIsUniversal to 1 (hardware clock interpreted as UTC)
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\TimeZoneInformation' -Name 'RealTimeIsUniversal' -Value 1 -Type DWord
# Force time resync after changing clock interpretation
w32tm /resync /rediscover
```

**Verification**:

```powershell
Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\TimeZoneInformation' -Name RealTimeIsUniversal -ErrorAction SilentlyContinue | Select-Object RealTimeIsUniversal
Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
```

Expected result: RealTimeIsUniversal = 1, system time displays correctly

**Risk notes**:

- **Session impact**: None; registry modification requires reboot to fully take effect.
- **Persistence scope**: Written to registry, retained after reboot.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\TimeZoneInformation' -Name 'RealTimeIsUniversal' -Value 0 -Type DWord`
- **Note**: Modifying this value changes how Windows interprets the hardware clock. If the current time has already been manually corrected due to incorrect configuration, the modification may cause the time to deviate again, requiring a re-sync with w32tm /resync. This modification requires a reboot to fully take effect (in some scenarios, resync alone can correct it).

---

### Root cause: W32Time Service Not Running

**Fix Action**:

```powershell
Set-Service -Name W32Time -StartupType Automatic
Start-Service -Name W32Time
# Force immediate sync
w32tm /resync /rediscover
```

**Verification**:

```powershell
Get-Service -Name W32Time | Select-Object Name, Status, StartType | Format-Table -AutoSize
```

Expected result: Status = Running, StartType = Automatic

**Risk notes**:

- **Session impact**: Forced sync may cause system time to jump.
- **Persistence scope**: StartupType change is retained after reboot.
- **Rollback command**: `Stop-Service -Name W32Time; Set-Service -Name W32Time -StartupType Manual`
- **Note**: Starting the W32Time service and forcing a sync will cause the system time to jump, which may affect applications that rely on a monotonic clock.

---

### Root cause: Secure Time Seeding Causing Time Jump

**Fix Action**:

```powershell
# Disable Secure Time Seeding (STS)
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Config' -Name 'UtilizeSslTimeData' -Value 0 -Type DWord
# Set reasonable phase correction limits (48 hours = 172800 seconds, Server default)
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Config' -Name 'MaxPosPhaseCorrection' -Value 172800 -Type DWord
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Config' -Name 'MaxNegPhaseCorrection' -Value 172800 -Type DWord
# Apply configuration without reboot
w32tm /config /update
# Force time resync from NTP source
w32tm /resync /rediscover
```

**Verification**:

```powershell
Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Config' -Name UtilizeSslTimeData, MaxPosPhaseCorrection, MaxNegPhaseCorrection -ErrorAction SilentlyContinue | Select-Object UtilizeSslTimeData, MaxPosPhaseCorrection, MaxNegPhaseCorrection
w32tm /query /source
Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
```

Expected result: UtilizeSslTimeData = 0, time source is an NTP server (not Local CMOS Clock), system time displays correctly

**Risk notes**:

- **Session impact**: Forced resync may cause system time to jump.
- **Persistence scope**: Registry configuration takes effect permanently, retained after reboot.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Config' -Name 'UtilizeSslTimeData' -Value 1 -Type DWord; w32tm /config /update`
- **Note**: After disabling STS, if the CMOS battery is depleted and NTP service is unavailable, the system will not be able to automatically correct severe time deviation. Cloud servers have reliable NTP service, so this risk is negligible. After modification, confirm that the W32Time service is running normally and the NTP configuration is valid.

**Emergency Recovery Tip**: If the time has already been jumped by STS and `w32tm /resync /rediscover` cannot correct it, initiate an SSL connection with correct time from within the instance (e.g., use a browser to visit any HTTPS website) to refresh the SecureTimeLimits cache; the time will automatically recover immediately; then follow the steps above to disable STS to prevent recurrence.

---

### Root cause: NTP Server Not Configured

**Applicable Root cause**: NTPServerNotConfigured

**Fix Action**:

```powershell
# Configure Alibaba Cloud NTP server
w32tm /config /manualpeerlist:"ntp.cloud.aliyuncs.com" /syncfromflags:manual /reliable:yes /update
# Restart time service
Restart-Service W32Time
# Force immediate sync
w32tm /resync /rediscover
```

**Verification**:

```powershell
w32tm /query /source
```

Expected result: Returns ntp.cloud.aliyuncs.com or other configured NTP server address

**Risk notes**:

- **Session impact**: None; the first sync after configuration change may take a few seconds to complete.
- **Persistence scope**: Written to registry, retained after reboot.
- **Rollback command**: `w32tm /config /manualpeerlist:"<OriginalNtpServer>" /syncfromflags:manual /reliable:yes /update; Restart-Service W32Time`
- **Note**: Switching the NTP server will change the time source; the first sync may take a few seconds to complete.

---

### Root cause: Incorrect Time Sync Type

**Applicable Root cause**: Type is NoSync

**Fix Action**:

```powershell
# Set sync type to NTP (for standalone server)
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Parameters' -Name 'Type' -Value 'NTP'
# Restart time service
Restart-Service W32Time
# Force immediate sync
w32tm /resync /rediscover
```

**Verification**:

```powershell
Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Parameters' -Name Type -ErrorAction SilentlyContinue | Select-Object Type
```

Expected result: Type = NTP

**Risk notes**:

- **Session impact**: None; modifying the sync type requires restarting the service to take effect.
- **Persistence scope**: Written to registry, retained after reboot.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Parameters' -Name 'Type' -Value 'NoSync'; Restart-Service W32Time`
- **Note**: Domain environments should use the NT5DS type; switching to NTP will cause domain time synchronization to fail. Standalone servers use the NTP type.

---

### Root cause: NTP Peer Unreachable

**Applicable Root cause**: NtpPeerUnreachable

**Fix Action**:

```powershell
# Check if UDP 123 outbound is blocked by firewall
Get-NetFirewallRule -Direction Outbound -Action Block -Enabled True -ErrorAction SilentlyContinue |
  Get-NetFirewallPortFilter -ErrorAction SilentlyContinue |
  Where-Object { $_.LocalPort -eq 123 -or $_.RemotePort -eq 123 } | Format-Table
# Test NTP server reachability (UDP 123)
w32tm /stripchart /computer:ntp.cloud.aliyuncs.com /samples:3 /dataonly
```

**Verification**:

```powershell
w32tm /resync /rediscover; Start-Sleep 3; w32tm /query /status
```

Expected result: Sync successful, Source shows a valid NTP server address

**Risk notes**:

- **Session impact**: None; diagnostics and firewall checks do not affect existing connections.
- **Persistence scope**: If firewall rules are added, they take effect permanently; if only testing connectivity, there are no persistent changes.
- **Rollback command**: `Remove-NetFirewallRule -DisplayName '<RuleName>'` (only applicable when new rules are added)
- **Note**: Cloud internal NTP (100.100.x.x) does not go through security groups but may be blocked by Windows firewall rules. First confirm that firewall/security group rules allow outbound UDP 123 traffic.

---

### Root cause: NTP Peer DNS Resolution Failure

**Applicable Root cause**: NtpDnsResolutionFailed

**Fix Action**:

```powershell
# Test DNS resolution for configured NTP servers
$ntpServers = (Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Parameters' -ErrorAction SilentlyContinue).NtpServer
if ($ntpServers) {
  $ntpServers -split ' ' | ForEach-Object {
    $server = ($_ -split ',')[0]
    Write-Host "Resolving: $server"
    Resolve-DnsName -Name $server -ErrorAction SilentlyContinue | Select-Object Name, IPAddress | Format-Table -AutoSize
  }
}
# If DNS fails, configure NTP with IP addresses directly
w32tm /config /manualpeerlist:"100.100.3.1 100.100.5.1 ntp.cloud.aliyuncs.com" /syncfromflags:manual /reliable:yes /update
Restart-Service W32Time
w32tm /resync /rediscover
```

**Verification**:

```powershell
w32tm /query /source
```

Expected result: Returns a valid NTP server address (IP or domain name)

**Risk notes**:

- **Session impact**: None; restarting the W32Time service after NTP configuration change takes effect immediately.
- **Persistence scope**: Written to registry, retained after reboot.
- **Rollback command**: `w32tm /config /manualpeerlist:"<OriginalNtpServers>" /syncfromflags:manual /update; Restart-Service W32Time`
- **Note**: Configuring NTP directly with IP addresses can bypass DNS issues, but IPs may change. The root cause of the DNS resolution failure (DNS server configuration, network connectivity) should be investigated simultaneously.

---

### Root cause: Excessive Clock Offset

**Applicable Root cause**: LargeClockOffset

**Fix Action**:

```powershell
# Force immediate time correction
w32tm /resync /rediscover
# If offset is too large for gradual correction, manually set time
# (Only use if resync fails to correct within reasonable time)
# w32tm /config /update
# net time /set /yes  # Use with caution
```

**Verification**:

```powershell
w32tm /stripchart /computer:ntp.cloud.aliyuncs.com /samples:3 /dataonly
```

Expected result: Offset is less than 128ms and stabilizing

**Risk notes**:

- **Session impact**: Time jump may cause Kerberos ticket invalidation, TLS certificate verification anomalies, and log timestamp jumps.
- **Persistence scope**: Time correction takes effect immediately and persists until the next drift.
- **Rollback command**: Time correction cannot be directly rolled back; if the time is set incorrectly, run `w32tm /resync /rediscover` again to re-sync.
- **Note**: Forced time jump may affect applications that rely on a monotonic clock. If the offset exceeds the MaxPosPhaseCorrection/MaxNegPhaseCorrection limits, automatic sync will be rejected; the limits need to be adjusted or the time needs to be set manually.

---

### Root cause: Clock Precision Interference (timeBeginPeriod High-Frequency Calls)

**Applicable Root cause**: ClockPrecisionInterference

**Fix Action**:

```powershell
# 1. Identify the interfering process: download and run CheckTimeBeginPeriod
#    https://changqu.oss-cn-hangzhou.aliyuncs.com/CheckTimeBeginPeriod.zip
#    (or use the stop-and-observe method)
# 2. If the culprit is the Cloud Assistant agent, upgrade it to the latest version (official build
#    has patched timeBeginPeriod/timeEndPeriod via API hook)
Get-Service -Name AliyunService -ErrorAction SilentlyContinue | Select-Object Name, Status, DisplayName
# Upgrade Cloud Assistant from the ECS console, or via:
#   https://help.aliyun.com/document_detail/64921.html (install/upgrade Cloud Assistant)
# 3. After eliminating the interference source, force one final sync to restore correct time
w32tm /resync /rediscover
```

**Verification**:

```powershell
# Observe clock drift over several hours; compare EventLog 6013 uptime increments
# (6013 is logged EVERY HOUR, so consecutive entries should be 3600 seconds apart)
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='EventLog'; Id=6013} -MaxEvents 25 -ErrorAction SilentlyContinue |
  Select-Object TimeCreated, Message | Format-List
```

Expected result: After eliminating the interference source, the time no longer drifts continuously, and the interval between consecutive 6013 events returns to approximately 3600 seconds (one per hour)

**Risk notes**:

- **Session impact**: None; upgrading/stopping the agent does not affect established sessions; stopping Cloud Assistant temporarily loses the remote command channel.
- **Persistence scope**: Upgrading the agent takes effect permanently.
- **Rollback command**: If a non-Cloud Assistant process was stopped and business is affected, restore that process and use a newer version (if a fix is available).
- **Note**: Do not rely solely on shortening the NTP sync interval to counter drift (this is treating the symptom, not the root cause, and frequent large corrections will cause time jumps); Server 2008 has ended mainstream support, and if the interference source cannot be upgraded, it is recommended that the user upgrade the operating system version.
