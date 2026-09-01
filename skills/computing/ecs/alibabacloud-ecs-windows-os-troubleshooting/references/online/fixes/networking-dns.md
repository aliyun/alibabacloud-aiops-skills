# DNS Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: DNS Client service abnormal

**Fix operation**:

```powershell
# Check current service status
Get-Service -Name Dnscache | Select-Object Name, Status, StartType | Format-Table -AutoSize

# If service is disabled, change startup type first
Set-Service -Name Dnscache -StartupType Automatic

# Start the service
Start-Service -Name Dnscache

# Verify service status
Get-Service -Name Dnscache | Select-Object Name, Status, StartType | Format-Table -AutoSize
```

**Verification**:

```powershell
Get-Service -Name Dnscache
```

Expected result: Status = Running, StartType = Automatic

**Risk notes**: Enabling the DNS Client service has no risk

---

### Root cause: DNS server configuration issue

**Fix operation**:

```powershell
# Get active network adapter
$adapter = Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object -First 1

if ($adapter) {
    # Configure Alibaba Cloud VPC DNS (for cloud servers)
    Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ServerAddresses @("100.100.2.136", "100.100.2.138")
    Write-Host "Configured DNS for adapter: $($adapter.Name)"
} else {
    Write-Host "No active network adapter found, please check network connection"
}
```

**Verification**:

```powershell
Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object {$_.ServerAddresses -ne $null} | Select-Object InterfaceAlias, ServerAddresses
```

Expected result: ServerAddresses contains 100.100.2.136 and 100.100.2.138

**Risk notes**: Modifying DNS affects all domain resolution; ensure VPC network policy allows access to the new DNS

---

### Root cause: DNS cache abnormal

**Fix operation**:

```powershell
# Clear DNS cache
Clear-DnsClientCache

ipconfig /flushdns

# Restart DNS Client service (optional, for thorough cleanup)
Restart-Service -Name Dnscache

# Verify cache is cleared
Get-DnsClientCache | Measure-Object | Select-Object Count
```

**Verification**:

```powershell
Resolve-DnsName -Name www.aliyun.com -Type A | Select-Object Name, IPAddress
```

Expected result: Can successfully resolve domain, cache count is zero

**Risk notes**: After clearing cache, first resolution may be slightly slower, usually harmless

---

### Root cause: hosts file issue

**Fix operation**:

```powershell
# 1. Backup current hosts file
Copy-Item C:\Windows\System32\drivers\etc\hosts C:\Windows\System32\drivers\etc\hosts.bak

# 2. Check hosts file encoding (should be ANSI or UTF-8 without BOM)
Get-Content C:\Windows\System32\drivers\etc\hosts -Encoding Default

# 3. Edit hosts file with Notepad (requires admin privileges)
notepad C:\Windows\System32\drivers\etc\hosts
```

Manual fix content:
- Delete or comment out lines that block domain resolution (e.g., `127.0.0.1 www.example.com`)
- Fix malformed lines (correct format: `IPAddress DomainName`)
- Remove duplicate domain mappings

```powershell
# 4. Fix file permissions
$acl = Get-Acl C:\Windows\System32\drivers\etc\hosts

# Remove all existing permissions
$acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) }

# Add correct permissions
$systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM", "FullControl", "Allow")
$adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "Allow")
$usersRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Users", "ReadAndExecute", "Allow")

$acl.AddAccessRule($systemRule)
$acl.AddAccessRule($adminRule)
$acl.AddAccessRule($usersRule)

Set-Acl C:\Windows\System32\drivers\etc\hosts $acl

# 5. Clear DNS cache to force reload of hosts file
Clear-DnsClientCache
```

**Verification**:

```powershell
# Check if domains in hosts file appear in cache (TTL=0)
Get-DnsClientCache | Where-Object {$_.TimeToLive -eq 0} | Select-Object Name, Data

# Test resolution of domains in hosts file
Resolve-DnsName -Name myserver.local -Type A | Select-Object Name, IPAddress
```

Expected result: Domains in hosts file appear in cache with TTL=0, and can correctly resolve to configured IP

**Risk notes**: hosts file encoding must be ANSI or UTF-8 without BOM; overly permissive permissions may lead to malicious modification of the file; some security software may modify the hosts file, confirm whether it is a malicious modification before deleting

---

### Root cause: Partial domain resolution failure

**Fix operation**:

```powershell
# Try using alternate DNS servers
$adapter = Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object -First 1

if ($adapter) {
    Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ServerAddresses @("100.100.2.136", "100.100.2.138")
}
```

**Verification**:

```powershell
Resolve-DnsName -Name www.aliyun.com -Type A | Select-Object Name, IPAddress
Resolve-DnsName -Name www.baidu.com -Type A | Select-Object Name, IPAddress
```

Expected result: Common domains can be resolved normally

**Risk notes**: Using multiple DNS servers can improve resolution success rate, but note that some domains may resolve differently on different DNS servers

---

### Root cause: DNS completely unavailable

**Fix operation**:

```powershell
# 1. Start DNS Client service
Set-Service -Name Dnscache -StartupType Automatic
Start-Service -Name Dnscache

# 2. Configure DNS servers
$adapter = Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object -First 1

if ($adapter) {
    Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ServerAddresses @("100.100.2.136", "100.100.2.138")
    Write-Host "Configured DNS for adapter: $($adapter.Name)"
} else {
    Write-Host "No active network adapter found"
}

# 3. Clear cache
Clear-DnsClientCache
```

**Verification**:

```powershell
Resolve-DnsName -Name www.aliyun.com -Type A | Select-Object Name, IPAddress
```

Expected result: Can successfully resolve domain

**Risk notes**: DNS completely unavailable is usually caused by service stopped or configuration error; after fix, verify network connectivity

---

### Root cause: DNS suffix and NRPT configuration issue

**Fix operation**:

```powershell
# Option 1: Configure DNS suffix search list (for short name resolution failure)
Set-DnsClientGlobalSetting -SuffixSearchList @("internal.aliyuncs.com", "aliyun.com") -UseSuffixSearchList $true

# Option 2: Configure connection-specific suffix for a specific adapter
$adapter = Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object -First 1

if ($adapter) {
    Set-DnsClient -InterfaceIndex $adapter.InterfaceIndex -ConnectionSpecificSuffix "internal.aliyuncs.com"
}

# Option 3: Remove problematic NRPT rule (if NRPT is blocking resolution)
# View current NRPT rules
Get-DnsClientNrptPolicy | Select-Object Namespace, NameServers

# Remove specific NRPT rule (requires admin privileges, proceed with caution)
# Remove-DnsClientNrptRule -Namespace "*.example.com" -Force
```

**Verification**:

```powershell
# Test short name resolution
Resolve-DnsName -Name myserver -Type A | Select-Object Name, IPAddress

# Check DNS suffix configuration
Get-DnsClientGlobalSetting | Select-Object SuffixSearchList, UseSuffixSearchList
```

Expected result: Short names can automatically append suffix and resolve successfully

**Risk notes**: DNS suffix search list affects all short name resolution, ensure suffix configuration is correct; NRPT is typically used in domain environments or DirectAccess/VPN, confirm whether it is required by enterprise security policy before deleting rules
