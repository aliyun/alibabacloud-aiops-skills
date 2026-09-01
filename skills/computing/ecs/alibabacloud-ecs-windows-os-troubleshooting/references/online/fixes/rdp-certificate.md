# RDP Certificate Diagnostic Fix Guide

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: RDP certificate expired

**Fix**:

```powershell
# Method 1: Delete expired certificate and let system auto-generate new self-signed certificate
# Enumerate all WinStations, check and delete expired certificates
$winStationsPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations"
Get-ChildItem -Path $winStationsPath -ErrorAction SilentlyContinue |
    Where-Object { $_.PSChildName -ne "Console" } |
    ForEach-Object {
        $stationName = $_.PSChildName
        $rdpCertThumbprint = (Get-ItemProperty -Path $_.PSPath -Name "SSLCertificateSHA1Hash" -ErrorAction SilentlyContinue).SSLCertificateSHA1Hash
        if ($rdpCertThumbprint) {
            # Custom certificate may reside in either the My or Remote Desktop store; search both (My first)
            $expiredCert = Get-ChildItem -Path "Cert:\LocalMachine\My", "Cert:\LocalMachine\Remote Desktop" -ErrorAction SilentlyContinue |
                Where-Object { $_.Thumbprint -eq (($rdpCertThumbprint | ForEach-Object { $_.ToString("X2") }) -join "") } |
                Select-Object -First 1
            if ($expiredCert -and $expiredCert.NotAfter -lt (Get-Date)) {
                Remove-Item -Path "$($expiredCert.PSPath)" -Force
                Write-Host "[$stationName] Deleted expired certificate from store: $($expiredCert.PSParentPath)"
            }
        }
    }

# Restart TermService to generate new certificate
Restart-Service -Name TermService -Force
Write-Host "Restarted TermService"
```

**Verification**:

```powershell
Get-ChildItem -Path "Cert:\LocalMachine\Remote Desktop", "Cert:\LocalMachine\My" | Select-Object Subject, NotAfter, Thumbprint
```

Expected result: A non-expired certificate exists

**Risk notes**:

- **Session impact**: Deleting the certificate will briefly interrupt RDP connections.
- **Persistence scope**: Certificate deletion is irreversible; the new certificate persists.
- **Rollback command**: Cannot restore the deleted certificate, but a self-signed certificate can be regenerated.
- **Note**: The new certificate is self-signed; clients will display a warning.

---

### Root cause: MachineKeys permissions abnormal

**Fix**:

```powershell
# Fix MachineKeys directory permissions
$machineKeysPath = "$env:ProgramData\Microsoft\Crypto\RSA\MachineKeys"
if (Test-Path $machineKeysPath) {
    # Restore Everyone read and write permissions
    $acl = Get-Acl -Path $machineKeysPath
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule("Everyone", "Read,Write,Synchronize", "Allow")
    $acl.SetAccessRule($rule)
    Set-Acl -Path $machineKeysPath -AclObject $acl
    Write-Host "Fixed MachineKeys directory permissions"
}
```

**Verification**:

```powershell
Get-Acl -Path "$env:ProgramData\Microsoft\Crypto\RSA\MachineKeys" |
    Select-Object -ExpandProperty Access |
    Where-Object {$_.IdentityReference -match "Everyone"}
```

Expected result: Everyone has Read,Write,Synchronize permissions

**Risk notes**:

- **Session impact**: None, only modifies file permissions.
- **Persistence scope**: Permission modifications persist across reboots.
- **Rollback command**: Manually remove the added ACL rule.
- **Note**: Modifying MachineKeys permissions affects all system certificates; proceed with caution.

---

### Root cause: RDP certificate missing

**Fix**:

```powershell
# Generate self-signed RDP certificate (requires administrator privileges)
$cert = New-SelfSignedCertificate -Type SSLServerAuthentication `
    -Subject "CN=RDP Self-Signed Certificate" `
    -CertStoreLocation "Cert:\LocalMachine\My" `
    -NotAfter (Get-Date).AddYears(1) `
    -KeyExportPolicy Exportable `
    -KeyLength 2048

# Configure new certificate for specified WinStation (replace <StationName> with actual station name)
$thumbprint = $cert.Thumbprint
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>" -Name "SSLCertificateSHA1Hash" -Value $thumbprint

Write-Host "Generated and configured new RDP self-signed certificate: $thumbprint"

# Restart service
Restart-Service -Name TermService -Force
```

**Verification**:

```powershell
$winStationsPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations"
Get-ChildItem -Path $winStationsPath -ErrorAction SilentlyContinue |
    Where-Object { $_.PSChildName -ne "Console" } |
    ForEach-Object {
        $hash = (Get-ItemProperty -Path $_.PSPath -Name "SSLCertificateSHA1Hash" -ErrorAction SilentlyContinue).SSLCertificateSHA1Hash
        [PSCustomObject]@{ Station = $_.PSChildName; SSLCertificateSHA1Hash = $hash }
    }
```

Expected result: The target WinStation's SSLCertificateSHA1Hash contains the new certificate thumbprint.

**Risk notes**:

- **Session impact**: Restarting TermService will briefly interrupt existing RDP connections.
- **Persistence scope**: Certificate and registry modifications persist across reboots.
- **Rollback command**: Delete the newly generated certificate and restore the original certificate configuration.
- **Note**: Self-signed certificates will cause clients to display warnings; CA-issued certificates are recommended for production environments.

---

### Root cause: TLS private key access denied

**Fix**:

```powershell
# Find TLS private key files
$programDataPath = (Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList" -Name "ProgramData" -ErrorAction SilentlyContinue).ProgramData
if (-not $programDataPath) { $programDataPath = $env:ProgramData }
$machineKeysPath = "$programDataPath\Microsoft\Crypto\RSA\MachineKeys"
$tlsKeys = Get-ChildItem -Path $machineKeysPath -Filter "f686aace*" -ErrorAction SilentlyContinue

if ($tlsKeys) {
    $tlsKeys | ForEach-Object {
        $acl = Get-Acl -Path $_.FullName

        # Add NETWORK SERVICE read permission
        $nsRule = New-Object System.Security.AccessControl.FileSystemAccessRule("NT AUTHORITY\NETWORK SERVICE", "Read", "Allow")
        $acl.SetAccessRule($nsRule)

        # Ensure SYSTEM has full control
        $sysRule = New-Object System.Security.AccessControl.FileSystemAccessRule("NT AUTHORITY\SYSTEM", "FullControl", "Allow")
        $acl.SetAccessRule($sysRule)

        Set-Acl -Path $_.FullName -AclObject $acl
        Write-Host "Fixed TLS private key file permissions: $($_.Name)"
    }
} else {
    Write-Host "No TLS private key files starting with f686aace found, may need to regenerate certificate"
}

# Restart TermService
Restart-Service -Name TermService -Force
```

**Verification**:

```powershell
$machineKeysPath = "$env:ProgramData\Microsoft\Crypto\RSA\MachineKeys"
Get-ChildItem -Path $machineKeysPath -Filter "f686aace*" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "File: $($_.Name)"
    (Get-Acl $_.FullName).Access | Where-Object { $_.IdentityReference -match 'NETWORK SERVICE|SYSTEM' } |
        Select-Object IdentityReference, FileSystemRights, AccessControlType | Format-Table -AutoSize
}
```

Expected result: NETWORK SERVICE has Read permission, SYSTEM has FullControl permission.

**Risk notes**:

- **Session impact**: Requires restarting TermService to take effect; will briefly interrupt RDP connections.
- **Persistence scope**: File permission modifications persist across reboots.
- **Rollback command**: Manually remove the added ACL rules.
- **Note**: If the private key file is missing, the certificate needs to be regenerated.

---

### Root cause: System drive root permissions abnormal

**Fix**:

```powershell
$systemDrive = $env:SystemDrive + "\\"
Write-Host "System drive root: $systemDrive"

$acl = Get-Acl -Path $systemDrive

# Add BUILTIN\Users read and execute permission
$usersRule = New-Object System.Security.AccessControl.FileSystemAccessRule("BUILTIN\Users", "ReadAndExecute", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.SetAccessRule($usersRule)

# Add NT AUTHORITY\SERVICE read permission
$serviceRule = New-Object System.Security.AccessControl.FileSystemAccessRule("NT AUTHORITY\SERVICE", "Read", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.SetAccessRule($serviceRule)

Set-Acl -Path $systemDrive -AclObject $acl
Write-Host "Fixed system drive root permissions"
```

**Verification**:

```powershell
$systemDrive = $env:SystemDrive + "\\"
(Get-Acl -Path $systemDrive).Access | Where-Object {
    $_.IdentityReference -match 'BUILTIN\\Users|NT AUTHORITY\\SERVICE'
} | Select-Object IdentityReference, FileSystemRights, AccessControlType | Format-Table -AutoSize
```

Expected result: BUILTIN\Users has ReadAndExecute permission, NT AUTHORITY\SERVICE has Read permission.

**Risk notes**:

- **Session impact**: None, only modifies file system permissions.
- **Persistence scope**: Permission modifications persist across reboots.
- **Rollback command**: Restore original ACL (back up current ACL before modifying).
- **Note**: Modifying system drive root permissions has a broad impact; proceed with caution.
