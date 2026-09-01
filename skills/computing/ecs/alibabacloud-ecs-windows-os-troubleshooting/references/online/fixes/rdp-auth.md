# RDP Authentication Diagnostic Fix Guide

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: CredSSP policy causing authentication failure / patch mismatch

> Scenario 1: Patched client cannot connect to unpatched server (most common)
> Scenario 2: Patched server rejects unpatched client connections (Force Updated mode)

**Temporary fix** (restores connection immediately but reduces security):

```powershell
# Set AllowEncryptionOracle to Vulnerable (2) on server to allow unpatched clients to connect
New-Item -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\CredSSP\Parameters" -Force -ErrorAction SilentlyContinue | Out-Null
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\CredSSP\Parameters" -Name "AllowEncryptionOracle" -Value 2 -Type DWord -Force
```

**Permanent fix** (recommended):

1. Install the cumulative update containing the CVE-2018-0886 fix on both server and client (see KB numbers in the table below)
2. After installation, restore AllowEncryptionOracle to a secure value:

| Operating System | Patch KB |
|---------|--------|
| Windows Server 2016 / Windows 10 1607 | KB4103723 |
| Windows Server 2012 R2 / Windows 8.1 | KB4103725 |
| Windows Server 2012 | KB4103730 |
| Windows Server 2008 R2 SP1 / Windows 7 SP1 | KB4103718 |

```powershell
# After installing patch, restore policy to secure value
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\CredSSP\Parameters" -Name "AllowEncryptionOracle" -Value 0 -Type DWord -Force
```

**Verification**:

```powershell
# Check policy value
Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\CredSSP\Parameters" -Name "AllowEncryptionOracle" -ErrorAction SilentlyContinue | Select-Object AllowEncryptionOracle

# Check TSpkg.dll version to confirm patch is installed
Get-Item "$env:SystemRoot\System32\TSpkg.dll" | Select-Object @{N='FileVersion';E={$_.VersionInfo.FileVersion}} | Format-Table -AutoSize
```

Expected result: After temporary fix, AllowEncryptionOracle = 2; after permanent fix, AllowEncryptionOracle = 0 and TSpkg.dll version meets the corresponding baseline.

**Risk notes**:

- **Session impact**: None, only modifies registry configuration.
- **Persistence scope**: Registry modifications persist across reboots.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\CredSSP\Parameters' -Name 'AllowEncryptionOracle' -Value 0`
- **Note**: The temporary fix (AllowEncryptionOracle=2) allows insecure CredSSP connections, posing a man-in-the-middle attack risk. Patches must be installed and the secure value restored as soon as possible.

---

### Root cause: Account lockout policy not configured

**Fix**:

```powershell
# Configure account lockout policy (example: lock after 5 failures, auto-unlock after 30 minutes)
net accounts /lockoutthreshold:5 /lockoutduration:30 /lockoutwindow:30
```

**Verification**:

```powershell
net accounts
```

Expected result: Lockout threshold / Lockout duration / Lockout observation window show the corresponding configured values.

**Risk notes**:

- **Session impact**: None, only modifies policy configuration.
- **Persistence scope**: Password policy modifications persist across reboots.
- **Rollback command**: `net accounts /lockoutthreshold:0` (disables lockout policy).
- **Note**: Configuring a lockout policy can prevent brute-force attacks, but ensure users are aware of the password policy.

---

### Root cause: RDP using native security layer

**Fix**:

```powershell
# Change specified WinStation security layer to Negotiate mode (replace <StationName> with actual station name)
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>" -Name "SecurityLayer" -Value 1

# Restart TermService
Restart-Service -Name TermService -Force
```

**Verification**:

```powershell
Get-ChildItem -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations" |
    Where-Object { $_.PSChildName -ne "Console" } |
    ForEach-Object { [PSCustomObject]@{ Station = $_.PSChildName; SecurityLayer = (Get-ItemProperty $_.PSPath).SecurityLayer } }
```

Expected result: Target WinStation SecurityLayer = 1

**Risk notes**:

- **Session impact**: Changing the security layer will interrupt existing RDP connections.
- **Persistence scope**: Registry modifications persist across reboots.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>' -Name 'SecurityLayer' -Value <OriginalValue>`

---

### Root cause: NLA not enabled

**Fix**:

```powershell
# Enable Network Level Authentication (NLA) for specified WinStation (replace <StationName> with actual station name)
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>" -Name "UserAuthentication" -Value 1

# Restart TermService
Restart-Service -Name TermService -Force
```

**Verification**:

```powershell
Get-ChildItem -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations" |
    Where-Object { $_.PSChildName -ne "Console" } |
    ForEach-Object { [PSCustomObject]@{ Station = $_.PSChildName; UserAuthentication = (Get-ItemProperty $_.PSPath).UserAuthentication } }
```

Expected result: Target WinStation UserAuthentication = 1

**Risk notes**:

- **Session impact**: Restarting TermService will briefly interrupt existing RDP connections.
- **Persistence scope**: Registry modifications persist across reboots.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\<StationName>' -Name 'UserAuthentication' -Value 0`
- **Note**: After enabling NLA, older RDP clients may not be able to connect.

---

### Root cause: Brute-force attack attempts or credential misconfiguration

**Fix**:

```powershell
# View recent login failure events
Get-WinEvent -FilterHashtable @{
    LogName = 'Security'
    ID = 4625
    StartTime = (Get-Date).AddHours(-1)
} -MaxEvents 20 | Select-Object TimeCreated, Message

# If brute force attack, configure IP security policy or use firewall to block source IP
# If credential error, remind user to use correct password
```

**Verification**:

```powershell
# Confirm whether login failure events have stopped
Get-WinEvent -FilterHashtable @{
    LogName = 'Security'
    ID = 4625
    StartTime = (Get-Date).AddMinutes(-10)
} -MaxEvents 5
```

Expected result: No new login failure events

**Risk notes**:

- **Session impact**: None, query and analysis operations only.
- **Persistence scope**: No configuration changes involved.
- **Rollback command**: No rollback needed.
- **Note**: If a brute-force attack is confirmed, it is recommended to configure account lockout policy and monitor security logs.

---

### Root cause: User lacks remote logon permission

**Fix**:

```powershell
# Add user to Remote Desktop Users group (replace <UserName> with actual username)
Add-LocalGroupMember -Group "Remote Desktop Users" -Member "<UserName>" -ErrorAction SilentlyContinue
Write-Host "Added user to Remote Desktop Users group"
```

**Verification**:

```powershell
Get-LocalGroupMember -Group "Remote Desktop Users" -ErrorAction SilentlyContinue | Select-Object Name, ObjectClass
```

Expected result: Target username appears in the list

**Risk notes**:

- **Session impact**: None, only adds group membership.
- **Persistence scope**: Group membership changes persist across reboots.
- **Rollback command**: `Remove-LocalGroupMember -Group 'Remote Desktop Users' -Member '<UserName>'`
- **Note**: Granting remote logon permission increases the system's attack surface.

---

### Root cause: User explicitly denied remote logon

**Fix**:

```powershell
# View current SeDenyRemoteInteractiveLogonRight configuration
secedit /export /cfg "$env:TEMP\secpol.cfg" /quiet
Select-String -Path "$env:TEMP\secpol.cfg" -Pattern "SeDenyRemoteInteractiveLogonRight"
Remove-Item "$env:TEMP\secpol.cfg" -ErrorAction SilentlyContinue

# Fix methods:
# 1. Modify via Local Security Policy editor (secpol.msc):
#    Local Policies > User Rights Assignment > Deny log on through Remote Desktop Services
#    Remove target user or group from the list
# 2. Or use ntrights tool (requires Windows Resource Kit):
#    ntrights -u <UserName> -r SeDenyRemoteInteractiveLogonRight
```

**Verification**:

```powershell
secedit /export /cfg "$env:TEMP\secpol.cfg" /quiet
Select-String -Path "$env:TEMP\secpol.cfg" -Pattern "SeDenyRemoteInteractiveLogonRight"
Remove-Item "$env:TEMP\secpol.cfg" -ErrorAction SilentlyContinue
```

Expected result: Target user or its group no longer appears in the SeDenyRemoteInteractiveLogonRight list.

**Risk notes**:

- **Session impact**: None, only modifies security policy.
- **Persistence scope**: Local security policy modifications persist across reboots. If set by domain policy, contact the domain administrator to modify.
- **Rollback command**: Re-add the user to SeDenyRemoteInteractiveLogonRight.
- **Note**: Removing the deny policy will allow the user to log on remotely.

---

### Root cause: Account locked out

**Fix**:

```powershell
# Unlock account (replace <UserName> with actual username)
$user = [ADSI]"WinNT://$env:COMPUTERNAME/<UserName>,user"
$user.IsAccountLocked = $false
$user.SetInfo()
```

**Verification**:

```powershell
# Replace <UserName> with actual username
Get-CimInstance -ClassName Win32_UserAccount -Filter "Name='<UserName>' AND LocalAccount=True" | Select-Object Name, Disabled, Lockout, Status
```

Expected result: Lockout = False

**Risk notes**:

- **Session impact**: None, only unlocks the account.
- **Persistence scope**: Unlocked state persists (unless lockout conditions are triggered again).
- **Rollback command**: No rollback needed (unlocking is a normal administrative operation).
- **Note**: Confirm it is not a brute-force attack before unlocking; if it is an attack, block the source IP first.

---

### Root cause: ForceGuest forced guest mode

**Fix**:

```powershell
# Set ForceGuest to Classic mode (0)
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa" -Name "ForceGuest" -Value 0
Write-Host "ForceGuest set to Classic mode (authenticate with user's own identity)"
```

**Verification**:

```powershell
(Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa" -Name "ForceGuest").ForceGuest
```

Expected result: ForceGuest = 0

**Risk notes**:

- **Session impact**: None, only modifies registry.
- **Persistence scope**: Registry modifications persist across reboots.
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -Name 'ForceGuest' -Value 1`
- **Note**: After disabling ForceGuest, remote users will authenticate using their own identity. Ensure account password strength is sufficient.
