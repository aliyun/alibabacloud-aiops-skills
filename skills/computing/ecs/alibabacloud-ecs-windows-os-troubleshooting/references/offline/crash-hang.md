# Crash and Hang Platform Diagnosis (Offline)

## Function Description

Offline diagnosis for instances that cannot boot normally after crash (BSOD) or hang (system frozen): First analyze dump files to obtain existing analysis conclusions; when the instance is still in a frozen state, guide the user to manually trigger NMI core collection and wait for dump file analysis conclusions; then proceed through the offline general analysis chain (driver / device tree / system configuration) for verification and fallback. In a frozen state, Cloud Assist is unreachable and in-instance collection commands are unavailable; diagnosis and analysis rely on dump file analysis and offline disk inspection.

**Input**: User problem description (required), crash / hang occurrence time (recommended)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

| User Problem Phenomenon | Recommended Steps |
|------------------------|-------------------|
| Cannot boot after crash (BSOD), repeated BSOD | Step 1 -> Step 3 |
| Cannot boot after hang / frozen, or hang recurs repeatedly | Step 1 -> Step 2 -> Step 3 |

## Diagnostic Steps

### Step 1: Dump File Analysis

**Data Collection**:

> Collection target: Analyze dump file content to obtain crash diagnostic analysis conclusions. Does not depend on offline disk environment, MUST be executed first before the offline disk prerequisite chain.

Analyze dump file content:

- Check whether dump files exist in `%SystemRoot%\Minidump\*`, `%SystemRoot%\MEMORY.DMP`
- If dump files exist, attempt to analyze their content to obtain BSOD root cause clues

**Analysis Approach**:

1. Dump file exists and is analyzable:
   - Analysis yields conclusion -> Use the dump analysis conclusion as the primary root cause clue, select the corresponding domain file in Step 3 for offline verification based on the direction indicated by the conclusion; present the analysis conclusion to the user truthfully
   - Dump file exists but cannot be analyzed -> No usable conclusion within the time window; for hang scenarios proceed to Step 2, otherwise proceed directly to Step 3
2. Dump file does not exist -> Record "dump file analysis skipped", proceed directly to Step 3

### Step 2: Hang Scenario Core Collection (Trigger NMI)

**Applicable Condition**: The user reports the phenomenon as system frozen / hang (no response to input), and Step 1 found no crash records.

**Analysis Approach**:

1. Instance is currently in "running + frozen" state -> Need to trigger NMI to crash the frozen system and produce a crash dump, which the crash platform collects and analyzes to provide a conclusion (i.e., "trigger core collection"). The trigger is performed manually by the user via the platform NMI injection page (crash management page "trigger core" entry); the diagnostic side is only responsible for pre-explanation and result follow-up:
   - **Image Support**: Windows only 2012R2 / 2016 / 2019 / 2022 / 2025 supports enabling NMI; if not in the supported list, inform the user that the image is not supported and proceed directly to Step 3
   - **Force Stop Authorization**: Triggering core collection requires the operator to have "Force Stop" authorization for the instance; if unauthorized, explain to the user that an approval process is required (can only be triggered after bpms approval passes)
   - **Kernel Memory Dump / NMI Enabled**: NMI depends on Kernel Memory Dump; both must be enabled in advance while the instance is running normally; in a frozen state, the enablement status cannot be queried or enabled. MUST explain this prerequisite to the user: if never enabled, collection is not possible this time; the user must enable Kernel Memory Dump and NMI after the instance recovers to normal operation, and collect during the next hang reproduction
   - **Risk Notes**: Triggering NMI will cause the instance to immediately BSOD and restart; current memory contents will be used as dump for crash platform analysis; MUST truthfully explain to the user and obtain confirmation before the user executes the trigger
   - Output the platform NMI injection page trigger operation instructions (crash management page "trigger core" entry) to the user, to be completed manually by the user; after core collection is complete, query the crash task by instance ID on the crash management page, and return to Step 1 to re-query the crash platform analysis conclusion
2. Instance has been stopped (hang resolved by forced restart) -> Cannot trigger NMI; inform the user that during the next hang reproduction, core collection must be manually triggered by the user while in a frozen state (prerequisites as above: image support, force stop authorization, Kernel Memory Dump / NMI enabled in advance), then proceed directly to Step 3

### Step 3: Offline General Analysis Chain

**Applicable Condition**: Dump file analysis yields no conclusion, or the analysis conclusion needs to be verified in the offline environment. After completing the offline disk prerequisite chain, check drivers, devices, and service configuration in order:

1. [driver.md](references/offline/driver.md): Boot-critical driver (VirtIO / storage / network) integrity, third-party filter driver residuals
2. [device-tree.md](references/offline/device-tree.md): Devices in the device enumeration tree that are disabled, have missing drivers, or have abnormal port instance counts
3. [system-config.md](references/offline/system-config.md): OS version, Sysprep status, critical file permissions, and abnormal service items

**Analysis Approach**:

1. When dump analysis conclusion points to a specific direction (driver / component / device), prioritize verifying the corresponding domain file
2. When the analysis conclusion or NMI collection requires raw dump evidence, dump files can be collected from the system disk in the offline environment (`%SystemRoot%\Minidump\*`, `%SystemRoot%\MEMORY.DMP`) for further analysis
3. Provide normal / abnormal conclusions item by item according to each domain file's judgment criteria; abnormal items are associated with specific root causes
4. If the general chain completes with no findings -> truthfully record the troubleshooting scope and all findings, recommend continuing along dynamically planned paths or escalating to expert support

## Cross-References

| Type | Trigger Condition | Target |
|------|-------------------|--------|
| Chain successor | Driver integrity / filter driver residual abnormality | -> [driver.md](references/offline/driver.md) |
| Chain successor | Device enumeration tree abnormality | -> [device-tree.md](references/offline/device-tree.md) |
| Chain successor | Service startup type / system configuration abnormality | -> [system-config.md](references/offline/system-config.md) |

## Fix Recommendations

This file does not define an independent fix block: fixes follow the domain to which the root cause belongs, executed according to the "Fix Recommendations" section of the corresponding domain file; dump analysis conclusion items are presented truthfully to the user along with the analysis conclusion.
