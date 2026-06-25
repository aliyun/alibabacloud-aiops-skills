# Windows SMB Mount Error Reference

## Auto-Check Script

```powershell
# Download inspection script
Invoke-WebRequest https://nas-client-tools.oss-cn-hangzhou.aliyuncs.com/windows_client/alinas_smb_windows_inspection.ps1 -OutFile alinas_smb_windows_inspection.ps1

# Run inspection script
.\alinas_smb_windows_inspection.ps1 -MountAddress <mount-target-address> -Locale zh-CN
```

## Correct SMB Mount Command

```cmd
net use <drive-letter> \\<mount-target-address>\myshare
```
Example: `net use z: \\xxxx.cn-hangzhou.nas.aliyuncs.com\myshare`

---

## System Error 53: Network Path Not Found

**Cause**: Network not connected, TCP/IP NetBIOS Helper service not started, or registry not correctly configured.

**Troubleshooting steps**:
1. `ping <mount-target-address>` to check network connectivity
2. Confirm mount command format is correct, no extra or missing `/`, `\`, spaces, or `myshare`
3. Confirm in the console that file system type is SMB
4. Confirm mount target address is correct
5. Confirm ECS and mount target are in the same VPC
6. `telnet <mount-target-address> 445` to check SMB service
7. Confirm TCP/IP NetBIOS Helper service is started
8. Check registry `HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\NetworkProvider\Order` to verify `ProviderOrder` contains `LanmanWorkstation`
9. Check if Windows Advanced Firewall is blocking SMB requests

## System Error 58: The Specified Server Cannot Perform the Requested Operation

**Cause**: Client SMB protocol version incompatible.

**Solution**: Confirm Windows version is Windows 2008 R2 or above (excluding Windows 2008).

## System Error 64: The Specified Network Name Is No Longer Available

**Cause**: Permission group unauthorized, account in arrears, UID mismatch in classic network, or file system type is not SMB.

**Troubleshooting steps**:
1. Confirm permission group includes the ECS private IP or VPC IP
2. Confirm account is not in arrears
3. For classic network mounting, confirm ECS and NAS belong to the same UID
4. Confirm file system type is SMB

## System Error 67: The Network Name Cannot Be Found

**Cause**: Critical network services not started.

**Solution**:
1. Enable Workstation service
2. Enable TCP/IP NetBIOS Helper service

## System Error 85: The Local Device Name Is Already In Use

**Cause**: Target drive letter is already occupied.

**Solution**: Use a different drive letter to remount.

## System Error 1231: Cannot Connect to Network Location

**Cause**: Microsoft network client/file and printer sharing not installed or enabled.

**Resolution steps**:
1. Open "Network and Sharing Center" → Click the connected network → Properties
2. Install Microsoft network client:
   - Select "Client" → Add → `Client for Microsoft Networks` → OK
3. Install file and printer sharing:
   - Select "Service" → Add → `Microsoft` → `File and Printer Sharing for Microsoft` → OK

## System Error 1272: Organization Security Policy Blocks Unauthenticated Guest Access

**Cause**: Windows security policy blocks Guest Auth access. Applies to Windows Server 2016 and later versions.

**Resolution steps**:
1. Open Registry Editor (`regedit`)
2. Path: `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters`
3. Set `AllowInsecureGuestAuth` to `1`
4. If it does not exist, create via PowerShell:
   ```powershell
   New-ItemProperty -Path Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters -Name AllowInsecureGuestAuth -PropertyType DWORD -Value 1
   ```
5. If error persists, check if `RequireSecuritySignature` under the same path is set to `1`, change to `0`

## System Error 3227320323: Digital Signing Policy Conflict

**Cause**: Windows has enabled the "Microsoft network client: Digitally sign communications (always)" policy.

**Resolution steps**:
1. `Win+R` type `gpedit.msc`
2. Path: Computer Configuration → Windows Settings → Security Settings → Local Policies → Security Options
3. Double-click "Microsoft network client: Digitally sign communications (always)"
4. Select "Disabled" → OK

## System Error 1312

**Cause**: When using PowerShell `New-SmbGlobalMapping` to mount, the entered username or workgroup is incorrect.

**Solution**: Check the correct workgroup name in "Computer → Properties", use the correct username (e.g. `workgroup\administrator`) and password.

---

## Windows NFS Mount Errors

### Invalid File Handle (file handle error)

**Resolution steps**:
1. Open Registry Editor, path: `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\ClientForNFS\CurrentVersion\Users\Default\Mount`
2. Create new DWORD (32-bit) value, name `Locking`, data `1`
3. Restart ECS
4. Remount: `mount -o nolock -o mtype=hard -o timeout=60 \\<mount-target-address>\! Z:`
5. Run `mount` to verify; output must contain `mount=hard`, `locking=no`, `timeout>=10`

### Network Error 53

**Solution**: Remount following the correct steps and parameter configuration.

### Network Error 1222

**Solution**: Install NFS client and then remount.

### Windows NFS Soft Mount Issue

**Risk**: Soft mode can cause data inconsistency and abnormal application exits.

**Resolution steps**:
1. Run `mount` command to check current mount mode
2. If it shows `mount=soft`:
   - Stop applications using the file system
   - Unmount: `umount H:`
   - Remount (hard mode): `mount -o nolock -o mtype=hard -o timeout=60 \\<mount-target-address>\! h:`
3. Verify mount result must contain `mount=hard`, `locking=no`, `timeout>=10`

### Windows Server 2016 IIS Cannot Load SMB Volume

**Solution**: AD domain installation and configuration is required.
