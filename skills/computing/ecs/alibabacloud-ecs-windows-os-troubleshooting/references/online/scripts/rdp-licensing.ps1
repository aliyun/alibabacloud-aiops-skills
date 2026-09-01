$ProgressPreference = 'SilentlyContinue'

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Remote Desktop Session Host Role Check ---

try {
    @('TermService', 'SessionEnv', 'UmRdpService') | ForEach-Object {
        Get-Service -Name $_ | Select-Object Name, Status, StartType
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 rds-services: " + $_.Exception.Message)
}

try {
    Get-WindowsFeature -Name RDS-RD-Server | Select-Object Name, DisplayName, InstallState | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 rdsh-role: " + $_.Exception.Message)
}

try {
    Get-WindowsFeature -Name RDS-Licensing | Select-Object Name, DisplayName, InstallState | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 rd-licensing-role: " + $_.Exception.Message)
}

# --- Step 2: RDS Licensing Mode Configuration Check ---

try {
    $tss = Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TerminalServiceSetting"
    if ($tss -and $tss.TerminalServerMode -ne 0) {
        $tss | Select-Object LicensingType, LicensingName, PolicySourceLicensingType, PossibleLicensingTypes | Format-Table -AutoSize

        Invoke-CimMethod -InputObject $tss -MethodName GetSpecifiedLicenseServerList
    } else {
        [PSCustomObject]@{
            TerminalServerMode = if ($tss) { $tss.TerminalServerMode } else { 'N/A' }
            Note               = 'RDSH not in application server mode; RDS licensing check not applicable'
        } | Format-List
    }
} catch {
    Write-Host ("ERROR step2 licensing-mode: " + $_.Exception.Message)
}

# --- Step 3: Grace Period Status Check ---

try {
    $tss = Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TerminalServiceSetting"
    if ($tss -and $tss.TerminalServerMode -ne 0) {
        $tss | Select-Object LicensingType, LicensingName | Format-Table -AutoSize
        Invoke-CimMethod -InputObject $tss -MethodName GetGracePeriodDays

        Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TSLicenseKeyPack" | Select-Object KeyPackType, ProductType, TotalLicenses, IssuedLicenses, AvailableLicenses | Format-List
    } else {
        [PSCustomObject]@{
            TerminalServerMode = if ($tss) { $tss.TerminalServerMode } else { 'N/A' }
            Note               = 'RDSH not in application server mode; Grace Period check not applicable'
        } | Format-List
    }
} catch {
    Write-Host ("ERROR step3 grace-period: " + $_.Exception.Message)
}

# --- Step 4: License Server Connectivity Check ---

try {
    $tss = Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TerminalServiceSetting"
    if ($tss -and $tss.TerminalServerMode -ne 0) {
        Invoke-CimMethod -InputObject $tss -MethodName GetSpecifiedLicenseServerList

        Invoke-CimMethod -InputObject $tss -MethodName GetTStoLSConnectivityStatus
    } else {
        [PSCustomObject]@{
            TerminalServerMode = if ($tss) { $tss.TerminalServerMode } else { 'N/A' }
            Note               = 'RDSH not in application server mode; license server connectivity check not applicable'
        } | Format-List
    }
} catch {
    Write-Host ("ERROR step4 license-server-connectivity: " + $_.Exception.Message)
}

try {
    Get-Service -Name TermServLicensing | Select-Object Name, Status, StartType | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 termservlicensing: " + $_.Exception.Message)
}

try {
    Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TSDeploymentLicensing" | Select-Object LicenseServer, LicenseServerType | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 licensing-discovery: " + $_.Exception.Message)
}
