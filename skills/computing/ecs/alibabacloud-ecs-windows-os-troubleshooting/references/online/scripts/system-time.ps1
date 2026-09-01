$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Time Zone and Daylight Saving Time Configuration Check ---
try {
    Get-TimeZone | Select-Object Id, DisplayName, BaseUtcOffset, SupportsDaylightSavingTime | Format-Table -AutoSize
    [PSCustomObject]@{
      'LocalTime' = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
      'UTCTime'   = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss')
      'Offset'    = ((Get-Date) - (Get-Date).ToUniversalTime()).ToString()
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 timezone: " + $_.Exception.Message)
}

# --- Step 2: RealTimeIsUniversal Check ---
try {
    # RealTimeIsUniversal is optional (absence = RTC interpreted as local time); whole-key read
    $tzi = Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\TimeZoneInformation'
    [PSCustomObject]@{
      'RealTimeIsUniversal' = $tzi.RealTimeIsUniversal
      'TimeZoneKeyName'     = $tzi.TimeZoneKeyName
      'StandardName'        = $tzi.StandardName
      'Bias'                = $tzi.Bias
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 tz-registry: " + $_.Exception.Message)
}
try {
    Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object Manufacturer, Model, HypervisorPresent | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 computer-system: " + $_.Exception.Message)
}
try {
    # Boot time loaded from hardware clock (QEMU provides local time, interpreted by system time zone)
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-General'; Id=12} -MaxEvents 5 |
      Select-Object TimeCreated, Message | Format-List
} catch {
    Write-Host ("ERROR step2 boot-time-events: " + $_.Exception.Message)
}

# --- Step 3: W32Time Service and NTP Sync Status Check ---
try {
    Get-Service -Name W32Time |
      Select-Object Name, Status, StartType |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 w32time-service: " + $_.Exception.Message)
}
try {
    $w32src = w32tm /query /source 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step3 w32tm-source: exit=$LASTEXITCODE $(($w32src | Out-String).Trim())" }
    $w32src
} catch {
    Write-Host ("ERROR step3 w32tm-source: " + $_.Exception.Message)
}
try {
    $w32status = w32tm /query /status 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step3 w32tm-status: exit=$LASTEXITCODE $(($w32status | Out-String).Trim())" }
    $w32status
} catch {
    Write-Host ("ERROR step3 w32tm-status: " + $_.Exception.Message)
}
try {
    # Time-Service sync events: 35/37 = sync success, 36/47 = sync failure warnings,
    # 50 = offset too large (over 15 min) auto-sync refused, 134/135/139/143 = source/hierarchy errors
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Time-Service'; Id=35,36,37,47,50,134,135,139,143} -MaxEvents 20 |
      Select-Object TimeCreated, Id, Message | Format-List
} catch {
    Write-Host ("ERROR step3 timeservice-events: " + $_.Exception.Message)
}
try {
    # Hourly uptime record (EventLog 6013 is logged EVERY HOUR): delta between two
    # consecutive entries should be 3600 seconds; a significant deviation indicates
    # clock drift or NTP sync not taking effect
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='EventLog'; Id=6013} -MaxEvents 25 |
      Select-Object TimeCreated, Message | Format-List
} catch {
    Write-Host ("ERROR step3 uptime-6013: " + $_.Exception.Message)
}

# --- Step 4: Secure Time Seeding (STS) Check ---
try {
    # Individual values are optional; whole-key read keeps absent ones as null
    $w32tConfig = Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Config'
    [PSCustomObject]@{
      'UtilizeSslTimeData'    = $w32tConfig.UtilizeSslTimeData
      'MaxPosPhaseCorrection' = $w32tConfig.MaxPosPhaseCorrection
      'MaxNegPhaseCorrection' = $w32tConfig.MaxNegPhaseCorrection
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 w32time-config: " + $_.Exception.Message)
}
try {
    # Event ID 1 has multiple sources: filter ProviderName in FilterHashtable directly,
    # "latest N + filter afterwards" can return nothing. Default window: last 30 days;
    # MUST narrow around the user-reported time jump point when provided.
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-General'; Id=1; StartTime=(Get-Date).AddDays(-30)} -MaxEvents 10 |
      Select-Object TimeCreated, Message | Format-List
} catch {
    Write-Host ("ERROR step4 time-change-events: " + $_.Exception.Message)
}
try {
    Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Time-Service/Operational'; Id=52,58,142} -MaxEvents 10 |
      Select-Object TimeCreated, Id, Message | Format-List
} catch {
    Write-Host ("ERROR step4 ts-operational-events: " + $_.Exception.Message)
}
try {
    # SSL time cache used by Secure Time Seeding (FILETIME values); its priority is HIGHER than NTP.
    # If current time deviates from SecureTimeEstimated by more than 15 hours, W32Time jumps the clock
    # immediately and /resync /force cannot correct it until a fresh SSL connection refreshes the cache.
    # Key absent is normal (STS disabled or no SSL time cached yet, e.g. Server 2012 R2 and earlier).
    $stl = Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\SecureTimeLimits'
    if ($stl) {
      $ste = $stl.SecureTimeEstimated
      $sth = $stl.SecureTimeHigh
      $stlLow = $stl.SecureTimeLow
      [PSCustomObject]@{
        'SecureTimeEstimated' = if ($ste -is [int64] -and $ste -ne 0) { [DateTime]::FromFileTime($ste).ToString('yyyy-MM-dd HH:mm:ss') } else { 'N/A' }
        'SecureTimeHigh'      = if ($sth -is [int64] -and $sth -ne 0) { [DateTime]::FromFileTime($sth).ToString('yyyy-MM-dd HH:mm:ss') } else { 'N/A' }
        'SecureTimeLow'       = if ($stlLow -is [int64] -and $stlLow -ne 0) { [DateTime]::FromFileTime($stlLow).ToString('yyyy-MM-dd HH:mm:ss') } else { 'N/A' }
        'CurrentTime'         = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
      } | Format-Table -AutoSize
    } else {
      Write-Host 'SecureTimeLimits key not found (STS disabled or no SSL time cached)'
    }
} catch {
    Write-Host ("ERROR step4 secure-time-limits: " + $_.Exception.Message)
}

# --- Step 5: NTP Server Registry Configuration Check ---
try {
    Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Parameters' |
      Select-Object NtpServer, Type |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 ntp-parameters: " + $_.Exception.Message)
}
try {
    Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpClient' |
      Select-Object SpecialPollInterval, Enabled |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 ntp-client: " + $_.Exception.Message)
}
try {
    Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpServer' |
      Select-Object Enabled |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 ntp-server: " + $_.Exception.Message)
}

# --- Step 7: clock precision interference check (timeBeginPeriod) ---
try {
    # OS version check: Windows Server 2008/2008 R2 (6.0/6.1) is especially affected
    Get-CimInstance -ClassName Win32_OperatingSystem |
      Select-Object Caption, Version, BuildNumber, OSArchitecture |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step7 os-version: " + $_.Exception.Message)
}
try {
    # Cloud Assistant service status (old golang build caused time drift on Server 2008,
    # fixed in newer builds via API hook patch; upgrading resolves the issue)
    Get-Service -Name AliyunService |
      Select-Object Name, Status, DisplayName |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step7 aliyun-service (may not be installed): " + $_.Exception.Message)
}
# NOTE: Identifying the actual caller of timeBeginPeriod cannot be done from a script
# (no observable channel for winmm API calls). Ask the user to download and run the
# CheckTimeBeginPeriod tool:
#   https://changqu.oss-cn-hangzhou.aliyuncs.com/CheckTimeBeginPeriod.zip
# or stop the suspect program and observe whether the drift stops.
# Process-name guessing is deliberately NOT collected here because the caller can be
# any process and a fixed name list would produce misleading evidence.
