$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: sppsvc Service Status Check ---
try {
    Get-CimInstance Win32_Service -Filter "Name='sppsvc'" |
      Select-Object Name, State, StartMode, Status, ExitCode | Format-List
} catch {
    Write-Host ("ERROR step1 sppsvc: " + $_.Exception.Message)
}

# --- Step 2: KMS Activation Status Check ---
try {
    Get-CimInstance -ClassName SoftwareLicensingProduct -Filter "PartialProductKey IS NOT NULL" |
      Select-Object Name, LicenseStatus, LicenseStatusReason, PartialProductKey, KeyManagementServiceMachine, KeyManagementServicePort | Format-List
} catch {
    Write-Host ("ERROR step2 licensing-product: " + $_.Exception.Message)
}

# --- Step 3: Product Key and KMS Configuration Check ---
try {
    Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber | Format-List
} catch {
    Write-Host ("ERROR step3 os-info: " + $_.Exception.Message)
}

try {
    Get-CimInstance -ClassName SoftwareLicensingProduct -Filter "PartialProductKey IS NOT NULL" |
      Select-Object Name, PartialProductKey, KeyManagementServiceMachine, KeyManagementServicePort |
      Format-List
} catch {
    Write-Host ("ERROR step3 kms-config: " + $_.Exception.Message)
}

try {
    # Outbound block rules that could deny KMS traffic (empty result = none, itself the finding)
    $kmsPort = 1688
    Get-NetFirewallRule -Enabled True -Direction Outbound -Action Block | ForEach-Object {
        $rule = $_
        Get-NetFirewallPortFilter -AssociatedNetFirewallRule $rule | Where-Object {
            ($_.Protocol -eq 'TCP') -and (@($kmsPort, 'Any') -contains $_.RemotePort)
        } | ForEach-Object {
            [PSCustomObject]@{
                RuleName    = $rule.DisplayName
                Direction   = $rule.Direction
                Action      = $rule.Action
                Protocol    = $_.Protocol
                RemotePort  = $_.RemotePort
            }
        }
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 outbound-block-rules: " + $_.Exception.Message)
}

try {
    # -WarningAction SilentlyContinue only mutes the routine "performing diagnostics" progress
    # warning; the TcpTestSucceeded result (the actual signal) is unaffected.
    Test-NetConnection -ComputerName kms.cloud.aliyuncs.com -Port 1688 -WarningAction SilentlyContinue |
      Select-Object ComputerName, RemotePort, TcpTestSucceeded | Format-List
} catch {
    Write-Host ("ERROR step3 test-netconnection-kms: " + $_.Exception.Message)
}

# --- Step 4: Activation Event Log Check ---
try {
    # Filter ProviderName in FilterHashtable directly: the Application log is
    # high-volume, so "latest N + filter afterwards" returns nothing.
    $startTime = (Get-Date).AddHours(-24)
    Get-WinEvent -FilterHashtable @{
        LogName = 'Application'
        ProviderName = 'Microsoft-Windows-Security-SPP'
        Level = @(2, 3)
        StartTime = $startTime
    } -MaxEvents 20 | Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-List
} catch {
    Write-Host ("ERROR step4 spp-events: " + $_.Exception.Message)
}
