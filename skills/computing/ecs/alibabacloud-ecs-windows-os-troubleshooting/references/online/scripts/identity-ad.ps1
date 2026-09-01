$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Check SID Conflict ---

try {
    $computerSid = (Get-CimInstance Win32_UserAccount -Filter "LocalAccount=True" | Select-Object -First 1).SID
    if ($computerSid) {
        $machineSid = $computerSid.Substring(0, $computerSid.LastIndexOf('-'))
        Write-Host "Machine SID: $machineSid"
    } else {
        Write-Host "WARNING: Unable to retrieve Machine SID"
    }
} catch {
    Write-Host ("ERROR step1 machine-sid: " + $_.Exception.Message)
}
try {
    $imageState = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Setup\State' -Name 'ImageState').ImageState
    Write-Host "ImageState: $imageState"
} catch {
    Write-Host ("ERROR step1 image-state: " + $_.Exception.Message)
}
try {
    $sysprepState = Get-ItemProperty -Path 'HKLM:\SYSTEM\Setup\Status\SysprepStatus'
    if ($sysprepState) {
        Write-Host "CleanupState: $($sysprepState.CleanupState)"
        Write-Host "GeneralizationState: $($sysprepState.GeneralizationState)"
    }
} catch {
    Write-Host ("ERROR step1 sysprep-state: " + $_.Exception.Message)
}

# --- Step 2: Check Domain Secure Channel Status ---

try {
    $cs = Get-CimInstance Win32_ComputerSystem
    if ($cs) {
        $cs | Select-Object Name, Domain, DomainRole, PartOfDomain | Format-List
    }
    if ($cs -and $cs.PartOfDomain) {
        try {
            $result = Test-ComputerSecureChannel -Verbose 2>&1
            Write-Host "SecureChannel Test: $result"
        } catch {
            Write-Host "ERROR step2 secure-channel: $($_.Exception.Message)"
        }
        Get-Service Netlogon |
            Select-Object Name, Status, StartType |
            Format-Table -AutoSize
    } else {
        Write-Host "INFO: Computer is not domain-joined, skipping secure channel test"
    }
} catch {
    Write-Host ("ERROR step2 computer-system: " + $_.Exception.Message)
}

# --- Step 3: Check Domain Controller Reachability ---

try {
    $cs = Get-CimInstance Win32_ComputerSystem
    if ($cs -and $cs.PartOfDomain) {
        $domain = $cs.Domain
        Write-Host "Domain: $domain"
        try {
            $dcRecords = Resolve-DnsName -Name "_ldap._tcp.dc._msdcs.$domain" -Type SRV -ErrorAction Stop
            $dcRecords | Select-Object Name, NameTarget, Port, Priority | Format-Table -AutoSize
        } catch {
            Write-Host "ERROR step3 dc-srv-records: $($_.Exception.Message)"
        }
        try {
            $dc = (Resolve-DnsName -Name $domain -ErrorAction Stop | Select-Object -First 1).IPAddress
            if ($dc) {
                Write-Host "DC IP: $dc"
                $ldap = Test-NetConnection -ComputerName $dc -Port 389 -WarningAction SilentlyContinue
                Write-Host "LDAP (389): TcpTestSucceeded=$($ldap.TcpTestSucceeded)"
                $kerb = Test-NetConnection -ComputerName $dc -Port 88 -WarningAction SilentlyContinue
                Write-Host "Kerberos (88): TcpTestSucceeded=$($kerb.TcpTestSucceeded)"
            }
        } catch {
            Write-Host "ERROR step3 domain-resolve: $($_.Exception.Message)"
        }
    } else {
        Write-Host "INFO: Computer is not domain-joined"
    }
} catch {
    Write-Host ("ERROR step3 computer-system: " + $_.Exception.Message)
}

# --- Step 4: Check Computer Account Password ---

try {
    $csPwd = Get-CimInstance Win32_ComputerSystem
    if ($csPwd -and $csPwd.PartOfDomain) {
        $pwdAge = Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters'
        if ($pwdAge) {
            Write-Host "DisablePasswordChange: $($pwdAge.DisablePasswordChange)"
            Write-Host "MaximumPasswordAge: $($pwdAge.MaximumPasswordAge) days"
        }
        # Filter ProviderName in FilterHashtable -- pulling the latest N entries of the whole
        # System log and filtering afterwards almost always returns nothing (NETLOGON events are sparse).
        $netlogonEvents = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='NETLOGON'; Level=2,3; StartTime=(Get-Date).AddDays(-30)} -MaxEvents 20
        if ($netlogonEvents) {
            $netlogonEvents | Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-Table -AutoSize
        } else {
            Write-Host "No NETLOGON error or warning events found in the last 30 days"
        }
    } else {
        Write-Host "INFO: Computer is not domain-joined"
    }
} catch {
    Write-Host ("ERROR step4 netlogon: " + $_.Exception.Message)
}

# --- Step 5: Check LDAPS Connection ---

try {
    $cs = Get-CimInstance Win32_ComputerSystem
    if ($cs -and $cs.PartOfDomain) {
        $domain = $cs.Domain
        try {
            $dc = (Resolve-DnsName -Name $domain -ErrorAction Stop | Select-Object -First 1).IPAddress
            if ($dc) {
                $ldaps = Test-NetConnection -ComputerName $dc -Port 636 -WarningAction SilentlyContinue
                Write-Host "LDAPS (636): TcpTestSucceeded=$($ldaps.TcpTestSucceeded)"
            }
        } catch {
            Write-Host "ERROR step5 domain-resolve: $($_.Exception.Message)"
        }
        $ldapReg = Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\ldap' -Name 'LDAPClientIntegrity'
        $ldapSigning = if ($ldapReg) { $ldapReg.LDAPClientIntegrity } else { $null }
        Write-Host "LDAPClientIntegrity: $ldapSigning (0=none, 1=negotiate, 2=require)"
    } else {
        Write-Host "INFO: Computer is not domain-joined"
    }
} catch {
    Write-Host ("ERROR step5 ldaps: " + $_.Exception.Message)
}
