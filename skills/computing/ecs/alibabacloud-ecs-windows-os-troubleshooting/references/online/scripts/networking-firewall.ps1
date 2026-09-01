# User-configurable: change this to the port being diagnosed (e.g. 80, 443, 3389)
$TargetPort = 3389

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Firewall Service Status Check ---

try {
    Get-Service -Name MpsSvc |
        Select-Object Name, Status, StartType |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 mpssvc: " + $_.Exception.Message)
}

# --- Step 2: Firewall Dependent Service Check ---

try {
    @('BFE', 'netprofm') | ForEach-Object {
        Get-Service -Name $_ |
            Select-Object Name, DisplayName, Status, StartType
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 dependent-services: " + $_.Exception.Message)
}

# --- Step 3: Firewall Profile and Active Network Check ---

try {
    Get-NetFirewallProfile -All |
        Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 firewall-profiles: " + $_.Exception.Message)
}

try {
    Get-NetConnectionProfile |
        Select-Object Name, InterfaceAlias, NetworkCategory |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 connection-profiles: " + $_.Exception.Message)
}

# --- Step 4: Inbound Rule Match Check ---

try {
    $targetPort = $TargetPort
    $rules = Get-NetFirewallRule -Direction Inbound -Enabled True
    $allowRules = @()
    $blockRules = @()
    foreach ($rule in $rules) {
        $portFilter = $rule | Get-NetFirewallPortFilter
        $lp = $portFilter.LocalPort
        $matched = $false
        if ($lp -eq 'Any') {
            $matched = $true
        } elseif ($lp -match '^\d+-\d+$') {
            $range = $lp -split '-'
            if ($targetPort -ge [int]$range[0] -and $targetPort -le [int]$range[1]) { $matched = $true }
        } elseif ($lp -match ',') {
            if ($lp -split ',' -contains [string]$targetPort) { $matched = $true }
        } else {
            if ($lp -eq [string]$targetPort) { $matched = $true }
        }
        if ($matched) {
            $obj = [PSCustomObject]@{
                DisplayName = $rule.DisplayName
                Action      = $rule.Action
                Profile     = $rule.Profile
                Protocol    = $portFilter.Protocol
                LocalPort   = $portFilter.LocalPort
            }
            if ($rule.Action -eq 'Allow') { $allowRules += $obj }
            elseif ($rule.Action -eq 'Block') { $blockRules += $obj }
        }
    }
    Write-Output "=== Allow Rules ==="
    $allowRules | Format-Table -AutoSize
    Write-Output "=== Block Rules ==="
    $blockRules | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 inbound-rules: " + $_.Exception.Message)
}

# --- Step 5: Outbound Rule Block Check ---

try {
    Get-NetFirewallProfile -All |
        Select-Object Name, DefaultOutboundAction |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 outbound-profiles: " + $_.Exception.Message)
}

try {
    Get-NetFirewallRule -Direction Outbound -Action Block -Enabled True |
        Select-Object DisplayName, Profile |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 outbound-block-rules: " + $_.Exception.Message)
}

# --- Step 6: Group Policy Firewall Rule Merge Check ---

try {
    $gpFirewallPath = 'HKLM:\SOFTWARE\Policies\Microsoft\WindowsFirewall'
    if (Test-Path $gpFirewallPath) {
        Get-ChildItem $gpFirewallPath -Recurse | ForEach-Object {
            Get-ItemProperty $_.PSPath
        } | Select-Object PSPath, EnableFirewall, DefaultInboundAction, DefaultOutboundAction, AllowLocalPolicyMerge, AllowLocalIPsecPolicyMerge |
            Format-List
    } else {
        Write-Output "No Group Policy firewall configuration detected"
    }
} catch {
    Write-Host ("ERROR step6 gp-firewall-registry: " + $_.Exception.Message)
}

try {
    Get-NetFirewallProfile -All |
        Select-Object Name, AllowLocalFirewallRules, AllowLocalIPsecRules |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 local-rule-merge: " + $_.Exception.Message)
}

# --- Step 7: WFP Packet Drop and Filter Rule Location ---
# Note: WFP is independent of the firewall service; when the firewall is disabled, third-party software can still intercept traffic via WFP
# Mode A: historical snapshot (events recorded so far)
$tempNetEvents = "$env:TEMP\netevents.xml"
$tempFilters = "$env:TEMP\filters.xml"
try {
    $neteventsOut = netsh wfp show netevents file="$tempNetEvents" 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step7 wfp-netevents: exit=$LASTEXITCODE $(($neteventsOut | Out-String).Trim())" }
    $filtersOut = netsh wfp show filters file="$tempFilters" 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step7 wfp-filters: exit=$LASTEXITCODE $(($filtersOut | Out-String).Trim())" }

    # Mode B: for reproducible issues, reproduce the fault first, then re-run Mode A
    # commands above. The system maintains a circular buffer of recent netevents;
    # running show netevents immediately after reproduction captures fresh events.

    @($tempNetEvents, $tempFilters) | ForEach-Object {
        if (Test-Path $_) {
            Write-Output "$_ size: $([math]::Round((Get-Item $_).Length / 1KB, 1)) KB"
        } else {
            Write-Output "Export failed: $_"
        }
    }
} catch {
    Write-Host ("ERROR step7 wfp-export: " + $_.Exception.Message)
} finally {
    Remove-Item $tempNetEvents, $tempFilters -Force -ErrorAction SilentlyContinue
}
