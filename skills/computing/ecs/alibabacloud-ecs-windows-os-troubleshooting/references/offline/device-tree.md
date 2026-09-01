# Device Enumeration Tree Diagnosis

## Function Description

Check devices in the device enumeration tree (PCI/SCSI/Storage) that are disabled, have missing drivers, or have abnormal port instance counts. Storage devices being disabled can cause BSOD STOP 0x7B.

**Input**: Boot partition drive letter
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

This file has only 1 step, execute directly.

## Diagnostic Steps

### Step 1: Device Enumeration Tree Health Check

**Data Collection**:

> Collection target: Check devices in the device enumeration tree with abnormal instance counts, missing drivers, and disabled status

```powershell
$enumPath = "<CcsPath>\Enum"

# Bus types to check
$busTypes = @('PCI', 'SCSI', 'Storage')

$issues = @()
foreach ($bus in $busTypes) {
    $busPath = "${enumPath}\$bus"
    if (!(Test-Path $busPath)) { continue }
    Get-ChildItem $busPath -ErrorAction SilentlyContinue | ForEach-Object {
        $portName = $_.PSChildName
        $instances = Get-ChildItem $_.PSPath -ErrorAction SilentlyContinue
        foreach ($inst in $instances) {
            $props = Get-ItemProperty $inst.PSPath -ErrorAction SilentlyContinue
            # Check device disabled (ConfigFlags bit0 = CONFIGFLAG_DISABLED)
            if ($props.ConfigFlags -band 1) {
                $issues += [PSCustomObject]@{
                    Bus = $bus; Port = $portName; Instance = $inst.PSChildName
                    Issue = 'Disabled'; ConfigFlags = $props.ConfigFlags
                }
            }
            # Check device instance with no driver mapping (ConfigFlags=0 and Driver is empty)
            if (($props.ConfigFlags -eq 0 -or $null -eq $props.ConfigFlags) -and [string]::IsNullOrEmpty($props.Driver)) {
                $issues += [PSCustomObject]@{
                    Bus = $bus; Port = $portName; Instance = $inst.PSChildName
                    Issue = 'NoDriver'; ConfigFlags = $props.ConfigFlags
                }
            }
        }
    }
}
$issues | Format-List
```

**Analysis Approach**:

1. Device instance disabled (ConfigFlags bit0 = 1):
   - SCSI\* or Storage\* disabled -> **Root cause**: Storage device instance disabled, **Severity**: Critical (can cause STOP 0x7B)
   - ROOT\spaceport disabled -> **Severity**: Warning (Get-Disk and other cmdlets unavailable)
   - Other devices -> **Severity**: Info
2. Device instance has no driver mapping (ConfigFlags=0 and Driver field is empty):
   - -> **Root cause**: Device instance has no driver mapping, **Severity**: Warning
   - Note: ConfigFlags!=0 indicates the device is being adjusted (e.g., after update pending reboot), should be ignored
3. Port instance count exceeds limit (actual device count under Port > InstanceNumber declared):
   - -> **Root cause**: Device port instance count abnormal, **Severity**: Warning

## Cross-References

| Type | Trigger Condition | Target |
|------|-------------------|--------|
| Prerequisite | Requires SYSTEM HIVE loaded | -> [registry.md](references/offline/registry.md) |
| Chain successor | SCSI/Storage device disabled | -> [driver.md](references/offline/driver.md) Step 7 |


## Fix Recommendations

Fix plans for root causes confirmed in this file are described in [device-tree.md](references/offline/fixes/device-tree.md).
