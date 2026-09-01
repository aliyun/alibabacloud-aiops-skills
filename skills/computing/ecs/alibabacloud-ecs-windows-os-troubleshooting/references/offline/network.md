# Network Configuration Diagnostics

## Function Description

Checks network adapter driver installation status, NIC enable status, IP configuration correctness (compared with MetaServer), DNS reachability, VMware virtual NIC residuals, network class filter driver compliance, and non-VirtIO virtual NIC device identification.

**Input**: Boot partition drive letter, registry HIVE already loaded
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

This file contains 5 diagnostic steps, each with independent execution conditions:

| Step | Execution Condition |
|------|---------------------|
| Step 1: Network adapter driver | Always execute |
| Step 2: NIC status and IP configuration | Execute when Sysprep status is IMAGE_STATE_COMPLETE |
| Step 3: VMware virtual NIC residual | Always execute |
| Step 4: Network class filter drivers | Always execute |
| Step 5: Non-VirtIO virtual NIC devices | Always execute |

## Diagnostic Steps

### Step 1: Network Adapter Driver Check

> **DISM Mandatory Rules**: This step calls `Get-WindowsDriver`, MUST strictly follow the two rules in [dism.md](references/offline/dism.md) "DISM Mandatory Rules" -- after the call, HIVE is unloaded; before entering the next step, you MUST immediately remount the HIVE per [registry.md](references/offline/registry.md) Step 2.
>
> **No Substitution**: Do not substitute `reg query` for the Net class registry key in place of this step. Reason: `Get-WindowsDriver` returns the installed **driver package metadata** (inf name, signature status, source, version), while the registry Class key only reflects the currently bound driver instance and cannot cover scenarios where "driver package is staged but not bound" or "multiple versions coexist".

**Data Collection**:

> Collection target: Confirm that at least one network adapter driver (such as netkvm) is installed

```powershell
# Query third-party network adapter class drivers via DISM module (ref: dism.md "Standard Disk Cache Pattern")
$cacheDir = Join-Path $env:SystemRoot 'Temp\diag-cache'
New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
$cacheFile = Join-Path $cacheDir 'WindowsDriver.json'
if (Test-Path $cacheFile) {
    $allDrivers = Get-Content $cacheFile -Raw | ConvertFrom-Json
} else {
    $allDrivers = Get-WindowsDriver -Path "<BootLetter>:\"
    $allDrivers | ConvertTo-Json -Depth 4 | Set-Content $cacheFile -Encoding UTF8
}
$allDrivers | Where-Object { $_.ClassName -eq 'Net' } | Format-Table Driver, ProviderName, Date, Version -AutoSize
```

**Analysis**:

1. No network adapter class driver package found:
   - -> **Root cause**: Network adapter driver not installed, **Severity**: Warning
   - Note: This check is complementary to the netkvm check in driver.md Step 2

### Step 2: NIC Status and IP Configuration Check

**Data Collection**:

> Collection target: Check VirtIO NIC enable status, binding order, and IP configuration correctness

```powershell

# Context memory: If system-config.md Step 2 has already collected ImageState, the model can directly reuse it from session memory; if not collected, collect it below
$setup = Get-ItemProperty "<SoftPath>\Microsoft\Windows\CurrentVersion\Setup\State" -ErrorAction SilentlyContinue
$imageState = $setup.ImageState
"ImageState: $imageState"

if ($imageState -eq 'IMAGE_STATE_COMPLETE') {
    # Locate VirtIO NIC via Net class (PCI\VEN_1AF4&DEV_1000)
    $netClassPath = "<CcsPath>\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
    $instances = Get-ChildItem $netClassPath -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -match '^\d+$' }
    $virtioGuids = @()
    foreach ($inst in $instances) {
        $props = Get-ItemProperty $inst.PSPath -ErrorAction SilentlyContinue
        if ($props.DeviceInstanceID -like 'PCI\VEN_1AF4&DEV_1000*') {
            $virtioGuids += $props.NetCfgInstanceId
        }
    }

    # Get binding order from Tcpip\Linkage\Route
    $linkage = Get-ItemProperty "<CcsPath>\Services\Tcpip\Linkage" -ErrorAction SilentlyContinue
    $bindOrder = $linkage.Route

    # For each VirtIO NIC, read IP config from Tcpip\Parameters\Interfaces
    foreach ($nicGuid in $virtioGuids) {
        $ifPath = "<CcsPath>\Services\Tcpip\Parameters\Interfaces\$nicGuid"
        $ifProps = Get-ItemProperty $ifPath -ErrorAction SilentlyContinue
        $dhcp = $ifProps.EnableDHCP
        if ($dhcp -eq 1) {
            $ip = $ifProps.DhcpIPAddress
            $mask = $ifProps.DhcpSubnetMask
            $gw = $ifProps.DhcpDefaultGateway
            $dns = $ifProps.DhcpNameServer
        } else {
            $ip = $ifProps.IPAddress
            $mask = $ifProps.SubnetMask
            $gw = $ifProps.DefaultGateway
            $dns = $ifProps.NameServer
        }

        # Get device status from Enum
        $enumPath = "<CcsPath>\Enum"
        $devInst = $instances | Where-Object {
            (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).NetCfgInstanceId -eq $nicGuid
        }
        $devId = (Get-ItemProperty $devInst.PSPath -ErrorAction SilentlyContinue).DeviceInstanceID
        $devProps = Get-ItemProperty "${enumPath}\$devId" -ErrorAction SilentlyContinue
        $configFlags = $devProps.ConfigFlags

        [PSCustomObject]@{
            NicGuid     = $nicGuid
            ConfigFlags = $configFlags
            Status      = if (($configFlags -band 1) -eq 0) { 'OK' } else { 'Disabled' }
            DHCPEnabled = $dhcp
            IPAddress   = $ip
            SubnetMask  = $mask
            Gateway     = $gw
            DNS         = $dns
            BindOrder   = [array]::IndexOf($bindOrder, "`"$nicGuid`"")
        }
    } | Sort-Object BindOrder | Format-List
}
```

**Analysis**:

1. ImageState is not IMAGE_STATE_COMPLETE -> skip IP configuration check (system has not completed deployment; IP will be reset by Sysprep)
2. No VirtIO NIC found (virtioGuids is empty) -> cannot perform network configuration check (NIC driver issue, refer to Step 1)
3. VirtIO NIC ConfigFlags != 0 (NIC disabled):
   - -> **Root cause**: Default NIC disabled, **Severity**: Warning
4. Static IP configuration incorrect (when DHCPEnabled = 0, compare with MetaServer metadata):
   - IP address does not match MetaServer's PrivateIpv4 -> **Root cause**: Static IP configuration inconsistent with VPC, **Severity**: Warning
   - Gateway not in the same subnet -> **Root cause**: Gateway configuration error
5. DNS unreachable:
   - -> **Root cause**: DNS server unreachable, **Severity**: Warning

### Step 3: VMware Virtual NIC Residual Check

**Data Collection**:

> Collection target: Check whether VMware virtual NIC class registrations exist in the SOFTWARE registry

```powershell

# Search for VMware virtual NIC classes
$vmwarePath = "<SoftPath>\Classes\CLSID"
Get-ChildItem $vmwarePath -Recurse -ErrorAction SilentlyContinue | Where-Object {
    (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).'(default)' -like '*VMware*'
} | Select-Object PSPath
```

**Analysis**:

1. VMware virtual NIC class registration found:
   - -> **Root cause**: VMware virtual NIC class residual, **Severity**: Warning
   - May cause Windows network class enumeration anomalies

### Step 4: Network Class Filter Driver Check

**Data Collection**:

> Collection target: Check filter drivers for Net/NetClient/NetService device classes

```powershell

$netGuids = @{
    'Net'        = '{4d36e972-e325-11ce-bfc1-08002be10318}'
    'NetClient'  = '{4d36e973-e325-11ce-bfc1-08002be10318}'
    'NetService' = '{4d36e974-e325-11ce-bfc1-08002be10318}'
}

foreach ($class in $netGuids.Keys) {
    $guidStr = $netGuids[$class]
    $path = "<CcsPath>\Control\Class\$guidStr"
    $props = Get-ItemProperty $path -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        Class        = $class
        UpperFilters = $props.UpperFilters
        LowerFilters = $props.LowerFilters
    }
}
```

**Analysis**:

1. Network class device registry key does not exist -> **Root cause**: Network class device registry missing, **Severity**: Critical
2. Non-standard value exists in filter driver list:
   - Check whether the corresponding service's ImagePath exists
   - File does not exist -> **Root cause**: Network class filter driver residual (service file missing), **Severity**: Critical
   - File exists -> **Severity**: Warning (may be security software, flagged as non-standard)

### Step 5: Non-VirtIO Virtual NIC Device Check

**Data Collection**:

> Collection target: Enumerate all NIC device instances under the Net device class and identify non-VirtIO (non-`PCI\VEN_1AF4&DEV_1000`) NIC devices. ECS instances should use VirtIO NICs (netkvm); VMware/other virtual NICs residual from imported images, TAP/tunnel virtual NICs created by security software can interfere with binding order and routing, causing network failure after boot

```powershell
# Enumerate all NIC device instances under Net class, flag non-VirtIO devices
$netClassPath = "<CcsPath>\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
$instances = Get-ChildItem $netClassPath -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -match '^\d+$' }
$enumPath = "<CcsPath>\Enum"
$instances | ForEach-Object {
    $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
    $devId = "$($props.DeviceInstanceID)"
    $isVirtio = $devId -like 'PCI\VEN_1AF4&DEV_1000*'
    # Resolve ConfigFlags (device enabled/disabled) from Enum path
    $configFlags = $null
    if ($devId -ne '') {
        $devProps = Get-ItemProperty "${enumPath}\$devId" -ErrorAction SilentlyContinue
        $configFlags = $devProps.ConfigFlags
    }
    [PSCustomObject]@{
        DeviceInstanceID  = $devId
        DriverDesc        = $props.DriverDesc
        IsVirtio          = $isVirtio
        ConfigFlags       = $configFlags
        NetCfgInstanceId  = $props.NetCfgInstanceId
        MatchingDeviceId  = $props.MatchingDeviceId
    }
} | Format-List
```

**Analysis**:

1. Review each output device instance and classify into three categories:
   - VirtIO NIC (IsVirtio=True): Normal ECS NIC; status determined by Step 2
   - Physical/other hardware NIC (e.g., `PCI\VEN_xxxx` not 1AF4): Residual from imported image (VMware VMXNET/E1000, Hyper-V, other cloud vendor virtual NICs) -> suspected residual device
   - Non-PCI virtual NIC (e.g., `ROOT\NET`, TAP-Windows, tunnel adapter, security software virtual NIC) -> virtual NIC created by third-party software
2. Determination:
   - Non-VirtIO NIC device instance exists -> **Root cause**: Non-VirtIO virtual NIC residual (NonVirtioNicPresent), **Severity**: Warning; if Step 2 shows the VirtIO NIC is not first in binding order or the user's symptom is "network failure after boot", escalate to **Critical** (residual NIC may seize routing/gateway)
   - Non-VirtIO NICs all have ConfigFlags=0 (enabled) and participate in binding -> prioritize suspicion of interference, combined with Tcpip\Linkage\Route binding order evidence
   - Only VirtIO NICs present -> no findings in this step
3. Note: Some residual device instances may no longer have corresponding drivers (shown with exclamation mark in Device Manager); offline cannot directly determine runtime impact; needs to be combined with Step 1 driver package list and user symptoms for comprehensive judgment

## Cross-References

| Type | Trigger Condition | Target |
|------|-------------------|--------|
| Prerequisite | Registry HIVE must be loaded -- this file triggers the on-demand registry tier ([registry.md](references/offline/registry.md)) if not yet executed | -- |


## Fix Recommendations

The fix solutions corresponding to the root causes confirmed in this file can be found in [network.md](references/offline/fixes/network.md).
