$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: RDP Certificate Source and Status Check ---

# 1. Read global self-signed certificate info (SelfSignedCertificate / SelfSignedCertStore under WinStations key)
$winStationsPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations"
try {
    $selfSignedThumb = $null
    $wsProps = Get-ItemProperty -Path $winStationsPath
    if ($wsProps) {
        $selfSignedStore = $wsProps.SelfSignedCertStore
        if (-not $selfSignedStore) { $selfSignedStore = "Remote Desktop" }
        $bytes = $wsProps.SelfSignedCertificate
        if ($bytes) { $selfSignedThumb = ($bytes | ForEach-Object { $_.ToString("X2") }) -join "" }
    } else {
        $selfSignedStore = "Remote Desktop"
    }
    Write-Host "=== Global Self-Signed Certificate ==="
    Write-Host "  SelfSignedCertStore   : $selfSignedStore"
    Write-Host "  SelfSignedCertificate : $(if ($selfSignedThumb) { $selfSignedThumb } else { '(not set)' })"
} catch {
    Write-Host ("ERROR step1 winstations-global: " + $_.Exception.Message)
}

# 2. Check certificate propagation service
try {
    Write-Host "`n=== Certificate Propagation Service ==="
    Get-Service -Name CertPropSvc | Select-Object Name, Status, StartType | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 certpropsvc: " + $_.Exception.Message)
}

# 3. Check certificates per WinStation
try {
    Get-ChildItem -Path $winStationsPath |
        Where-Object { $_.PSChildName -ne "Console" } |
        ForEach-Object {
            $stationName = $_.PSChildName
            Write-Host "`n=== WinStation: $stationName ==="

            # SSLCertificateSHA1Hash is REG_BINARY, convert to hex thumbprint
            $sslHashBytes = (Get-ItemProperty -Path $_.PSPath -Name "SSLCertificateSHA1Hash").SSLCertificateSHA1Hash
            if ($sslHashBytes) {
                $thumb = ($sslHashBytes | ForEach-Object { $_.ToString("X2") }) -join ""
                # Custom certificate may reside in either the My or Remote Desktop store; search both (My first)
                $storeName = @("My", "Remote Desktop")
                $source = "Custom"
            } else {
                $thumb = $selfSignedThumb
                $storeName = @($selfSignedStore)
                $source = "SelfSigned (default)"
            }

            Write-Host "  Source    : $source"
            Write-Host "  CertStore : $(($storeName | ForEach-Object { "LocalMachine\$_" }) -join ', ')"
            Write-Host "  Thumbprint: $(if ($thumb) { $thumb } else { '(none)' })"

            if ($thumb) {
                $cert = Get-ChildItem -Path ($storeName | ForEach-Object { "Cert:\LocalMachine\$_" }) |
                        Where-Object { $_.Thumbprint -eq $thumb } |
                        Select-Object -First 1
                if ($cert) {
                    $cert | Select-Object Subject, Issuer, NotBefore, NotAfter, HasPrivateKey, Thumbprint | Format-List
                } else {
                    Write-Host "  [Abnormal] Certificate not found (thumbprint $thumb does not exist in $(($storeName | ForEach-Object { "LocalMachine\$_" }) -join ' or ') store)"
                }
            }
        }
} catch {
    Write-Host ("ERROR step1 winstation-certs: " + $_.Exception.Message)
}

# --- Step 2: MachineKeys and TLS Private Key Permission Check ---

# 1. Get ProgramData path (via registry to handle non-default paths)
try {
    $programDataPath = (Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList" -Name "ProgramData").ProgramData
    if (-not $programDataPath) { $programDataPath = $env:ProgramData }
    Write-Host "ProgramData path: $programDataPath"
} catch {
    Write-Host ("ERROR step2 programdata-path: " + $_.Exception.Message)
}

# 2. MachineKeys directory permission check
try {
    $machineKeysPath = "$programDataPath\Microsoft\Crypto\RSA\MachineKeys"
    Write-Host "--- MachineKeys Directory ACL ---"
    Get-Acl -Path $machineKeysPath |
        Select-Object -ExpandProperty Access |
        Where-Object { $_.IdentityReference -match 'Everyone|Administrators|SYSTEM' } |
        Select-Object IdentityReference, FileSystemRights, AccessControlType | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 machinekeys-acl: " + $_.Exception.Message)
}

# 3. TLS private key file check (f686aace prefix)
try {
    Write-Host "--- TLS Private Key Files (f686aace*) ---"
    try {
        $tlsKeys = Get-ChildItem -Path $machineKeysPath -Filter "f686aace*" -ErrorAction Stop
        if ($tlsKeys) {
            $tlsKeys | ForEach-Object {
                Write-Host "  File: $($_.Name)"
                $fileAcl = Get-Acl -Path $_.FullName
                $fileAcl.Access | Where-Object {
                    $_.IdentityReference -match 'NETWORK SERVICE|SYSTEM|Administrators'
                } | Select-Object IdentityReference, FileSystemRights, AccessControlType | Format-Table -AutoSize
            }
        } else {
            Write-Host "  No TLS private key files starting with f686aace found"
        }
    } catch {
        Write-Host "  ERROR step2 tls-key-files: $($_.Exception.Message)"
    }
} catch {
    Write-Host ("ERROR step2 tls-key-files: " + $_.Exception.Message)
}

# --- Step 3: System Drive Root Directory Permission Check ---

try {
    $systemDrive = $env:SystemDrive + "\\"
    Write-Host "System drive root: $systemDrive"
    (Get-Acl -Path $systemDrive).Access | Where-Object {
        $_.IdentityReference -match 'BUILTIN\\Users|NT AUTHORITY\\SERVICE'
    } | Select-Object IdentityReference, FileSystemRights, AccessControlType | Format-List
} catch {
    Write-Host ("ERROR step3 systemdrive-acl: " + $_.Exception.Message)
}
