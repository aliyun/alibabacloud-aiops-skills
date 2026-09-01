# Storage SMB Diagnostic Fix Plan

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: SMB Signature Requirement Causes Client Connection Failure

> Corresponding diagnosis: Step 1 (SMB Client Configuration Check) - Analysis approach item 1

**Fix operation**:

```powershell
# Disable mandatory signature requirement on client (allow connecting to SMB servers that do not support signing)
Set-SmbClientConfiguration -RequireSecuritySignature $false -Force
```

**Verification**:

```powershell
Get-SmbClientConfiguration | Select-Object RequireSecuritySignature, EnableSecuritySignature
```

Expected result: RequireSecuritySignature = False, EnableSecuritySignature = True

**Risk notes**:

- **Session impact**: None, only modifies client configuration without disrupting existing connections.
- **Persistence scope**: Permanent, retained across reboot.
- **Rollback command**: `Set-SmbClientConfiguration -RequireSecuritySignature $true -Force`
- **Note**: Disabling mandatory signing reduces SMB connection security and may expose the connection to man-in-the-middle attacks on untrusted networks. Only disable when connecting to SMB servers on internal trusted networks.

---

### Root cause: Windows Server 2025 Default Mandatory Signing Causes Third-Party SMB Connection Failure (System Error C05D0003)

> Corresponding diagnosis: Step 1 (SMB Client Configuration Check) - Analysis approach item 1

**Fix operation**:

```powershell
# Disable client mandatory signature requirement
Set-SmbClientConfiguration -RequireSecuritySignature $false -Force
```

**Verification**:

```powershell
# Check client signature configuration
Get-SmbClientConfiguration | Select-Object RequireSecuritySignature, EnableSecuritySignature | Format-Table -AutoSize

# Test connection to third-party SMB server
net use Z: \\nas-server\share /user:username password

# Or test using PowerShell
Test-Path \\nas-server\share

# Or use New-SmbGlobalMapping (for Server 2012+)
$credential = Get-Credential  # When entering username, format: DOMAIN\Username Note: must specify domain
New-SmbGlobalMapping -RemotePath "\\nas-server\share" -Credential $credential
```

Expected result:
- RequireSecuritySignature = False
- Successfully connected to the third-party SMB server with no C05D0003 error

**Risk notes**:

- **Session impact**: None, registry changes do not affect existing SMB connections; new connections take effect.
- **Persistence scope**: Written to registry, retained across reboot.
- **Rollback command**: `Set-SmbClientConfiguration -RequireSecuritySignature $true -Force`
- **Note**: Disabling mandatory signing reduces SMB connection security and may expose the connection to man-in-the-middle attacks on untrusted networks. Only use this when connecting to third-party SMB servers on internal trusted networks that do not support signing; in domain environments or public networks, it is recommended to keep signing enabled.

**Background**:
- Windows Server 2025 enables SMB mandatory signing by default (RequireSecuritySignature = True) for security reasons
- Earlier Windows versions (2022 and earlier) default to False (signing on demand)
- Third-party SMB implementations (such as Linux Samba, NAS devices, cloud storage) may not fully support SMB signing
- This issue primarily affects scenarios where Windows Server 2025 acts as a client connecting to third-party SMB servers
- New-SmbGlobalMapping is a PowerShell cmdlet introduced in Windows Server 2012 for creating global SMB mappings, which is more suitable for scripted operations than net use
- **Note**: When using New-SmbGlobalMapping, the credential format must be specified correctly:
  - Domain environment: `DOMAIN\Username`
  - Workgroup/local: `ComputerName\Username` or `.\Username` (use the `whoami` command to see the full format)
  - If the domain is not specified, the error "System error 1312: The specified session does not exist" will occur

---

### Root cause: Windows 10/Server 2016+ Default Blocks Insecure Guest Logon

> Corresponding diagnosis: Step 4 (Guest Access Policy Check) - Analysis approach item 1

**Fix operation**:

```powershell
# Enable insecure Guest logon (allow access to shares requiring Guest authentication)
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters" `
  -Name "AllowInsecureGuestAuth" -PropertyType DWORD -Value 1 -Force
```

**Verification**:

```powershell
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters" | `
  Select-Object AllowInsecureGuestAuth
```

Expected result: AllowInsecureGuestAuth = 1

**Risk notes**:

- **Session impact**: None, new connections will allow Guest access after enabling; existing connections are unaffected.
- **Persistence scope**: Written to registry, retained across reboot.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters' -Name 'AllowInsecureGuestAuth' -Value 0`
- **Note**: Enabling insecure Guest logon reduces security and allows unauthenticated access. Only enable when accessing shares on trusted networks. The best practice is to configure proper user authentication rather than relying on Guest access.

---

### Root cause: Guest Authentication Blocked (AllowInsecureGuestAuth = 0)

> Corresponding diagnosis: Step 4 (Guest Access Policy Check) - Analysis approach item 2

**Fix operation**:

```powershell
# Method 1: Enable Guest access (quick fix)
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters" `
  -Name "AllowInsecureGuestAuth" -Value 1

# Method 2: Use Credential Manager to save authentication info (recommended)
# cmdkey /add:<ServerName> /user:<UserName> /pass:<Password>

# Method 3: Modify Group Policy
# gpedit.msc -> Computer Configuration -> Administrative Templates -> Network -> Lanman Workstation
# Enable "Enable insecure guest logons"
```

**Verification**:

```powershell
# Check registry
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters" | `
  Select-Object AllowInsecureGuestAuth

# Try accessing the share
Test-Path "\\<Server>\<Share>"
```

Expected result: AllowInsecureGuestAuth = 1, share accessible

**Risk notes**:

- **Session impact**: None, new connections will allow Guest access after modification.
- **Persistence scope**: Written to registry, retained across reboot.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters' -Name 'AllowInsecureGuestAuth' -Value 0`
- **Note**: Guest access does not provide identity verification; anyone can access the share. In production environments, use domain authentication or local user authentication.

---

### Root cause: Microsoft Network Client Not Installed or Not Enabled

> Corresponding diagnosis: Step 2 (Network Component Status Check) - Analysis approach item 1

**Fix operation**:

```powershell
# Enable using PowerShell (Windows 8/Server 2012+)
Enable-NetAdapterBinding -Name "<AdapterName>" -ComponentID "ms_msclient"
```

**Verification**:

```powershell
# Check component status
Get-NetAdapterBinding -ComponentID "ms_msclient" | Select-Object Name, Enabled

# Verify using netcfg
netcfg -s n | Select-String "ms_msclient"
```

Expected result: ms_msclient installed and enabled

**Risk notes**:

- **Session impact**: Takes effect immediately after enabling; does not affect existing connections.
- **Persistence scope**: Binding state persists, retained across reboot.
- **Rollback command**: `Disable-NetAdapterBinding -Name '<AdapterName>' -ComponentID 'ms_msclient'`
- **Note**: Microsoft Network Client is a required component for accessing SMB shares. Disabling it prevents access to any SMB/CIFS network resources.

---

### Root cause: LanmanWorkstation Not Configured in Network Provider Order

> Corresponding diagnosis: Step 2 (Network Component Status Check) - Analysis approach item 3

**Fix operation**:

```powershell
# Add LanmanWorkstation to ProviderOrder
$registryPath = "HKLM:\SYSTEM\CurrentControlSet\Control\NetworkProvider\Order"
$currentOrder = (Get-ItemProperty -Path $registryPath).ProviderOrder

if ($currentOrder -eq "") {
    $newOrder = "LanmanWorkstation"
} else {
    $newOrder = "$currentOrder,LanmanWorkstation"
}

Set-ItemProperty -Path $registryPath -Name "ProviderOrder" -Value $newOrder

# Restart Workstation service
Restart-Service LanmanWorkstation -Force
```

**Verification**:

```powershell
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\NetworkProvider\Order" | `
  Select-Object ProviderOrder

# Test SMB connection
Test-Path "\\<Server>\<Share>"
```

Expected result: ProviderOrder contains LanmanWorkstation, SMB connection normal

**Risk notes**:

- **Session impact**: Restarting the Workstation service briefly interrupts all existing SMB connections.
- **Persistence scope**: Written to registry, retained across reboot.
- **Rollback command**: Remove LanmanWorkstation from ProviderOrder and restart the service.
- **Note**: Incorrect ProviderOrder configuration may cause SMB connection failures or priority issues. Restarting the Workstation service is required after modification.
