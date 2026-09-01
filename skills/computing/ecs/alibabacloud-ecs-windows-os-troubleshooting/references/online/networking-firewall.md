# Windows Firewall Diagnostics

## Function Description

Diagnoses Windows Firewall service, rule configuration, and traffic filtering issues. Covers firewall service and dependency service status, profile (Domain/Private/Public) enable and default action, inbound/outbound rule priority and conflicts, group policy rule merge strategy, WFP packet drop events and filter rule localization, and other scenarios.

**Input**: User problem description (required), blocked port/protocol/error code (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix / cross_ref)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Port inaccessible / Inbound blocked | Step 4 (Inbound rule matching) -> Step 3 (Profile and active network) |
| Application cannot connect to network / Outbound blocked | Step 5 (Outbound rules) -> Step 3 (Profile default outbound action) |
| Firewall rules not effective | Step 1 (Service status) -> Step 2 (Dependency services) -> Step 3 (Profile) |
| Group policy deployed rules not effective / Local rules overridden | Step 6 (Group policy rule merge) -> Step 3 (Profile) |
| Intermittent network disruption / Unexplained packet loss | Step 7 (WFP packet drop and filter rule localization) |
| Firewall disabled but still experiencing network anomalies | Step 7 (WFP packet drop and filter rule localization) -- WFP is independent of the firewall service; even with firewall disabled, third-party software can still inject filter rules through WFP |
| Ping reports "General failure" (any OS-language localized equivalent) | Step 7 FIRST (highest priority) -- this error text means the packet never left the local stack -> local filtering; run after at most a quick adapter/IP sanity glance |
| Outbound partially unreachable (some targets fail while others succeed) | Step 7 first -- selective target failure is the classic third-party WFP filter pattern |
| Firewall-related service crash or failure to start | Step 1 (Service status) -> Step 2 (Dependency services) |

## Diagnostic Steps

### Step 1: Firewall Service Status Check

**Data Collection**:

> Collection target: Obtain the running status and startup type of the Windows Firewall service (MpsSvc)

- PowerShell script: [networking-firewall.ps1](references/online/scripts/networking-firewall.ps1) Section Step 1

**Analysis Approach**:

1. Check firewall service running status:
   - Normal: Service is running
   - Abnormal: Service not running -> **Root cause**: Windows Firewall service not running, all firewall rules ineffective, **Severity**: Warning
   - Abnormal: Service startup type is Disabled -> **Root cause**: Windows Firewall service disabled, **Severity**: Warning
   - Note: Firewall service stopping does not mean all WFP filters are invalidated; third-party software can still intercept traffic through WFP; if unexplained packet loss exists, further check Step 7

> Note: When the firewall service is stopped, all rules become ineffective, and both inbound and outbound traffic are uncontrolled

### Step 2: Firewall Dependency Service Check

**Data Collection**:

> Collection target: Obtain the status of key services that the firewall depends on for normal operation, including Base Filtering Engine (BFE), Network List Service (netprofm)

- PowerShell script: [networking-firewall.ps1](references/online/scripts/networking-firewall.ps1) Section Step 2

**Analysis Approach**:

1. Check Base Filtering Engine (BFE) service:
   - Normal: Service is running
   - Abnormal: BFE not running -> **Root cause**: Base Filtering Engine service not running, WFP and firewall completely ineffective, **Severity**: Critical

2. Check Network List Service:
   - Normal: Service is running
   - Abnormal: netprofm not running -> **Root cause**: Network List Service not running, affects network profile identification, **Severity**: Warning

### Step 3: Firewall Profile and Active Network Check

**Data Collection**:

> Collection target: Obtain enable status of all firewall profiles, default inbound/outbound actions, and the profile type corresponding to the current active network connection

- PowerShell script: [networking-firewall.ps1](references/online/scripts/networking-firewall.ps1) Section Step 3

**Analysis Approach**:

1. Check profile enable status:
   - Normal: At least one profile is enabled
   - Normal: All profiles disabled -> In cloud environments this is an expected configuration; the cloud platform provides network-layer protection through security groups; firewall rules being ineffective poses no security risk
   - **If all profiles are disabled, skip the rule checks in Step 4/5 below**

2. Check the profile type corresponding to the current active network:
   - Normal: Network type is DomainAuthenticated, Private, or Public (cloud instances default to Public, which is an expected configuration)
   - Attention: Network type misidentification needs to be analyzed in conjunction with other factors. For in-depth investigation, see -> [networking-tcpip.md](references/online/networking-tcpip.md)

3. Check default outbound action:
   - Normal: Default outbound action is Allow (expected configuration for most deployments)
   - Abnormal: Default outbound action is Block -> **Root cause**: Firewall profile default blocking outbound connections, all outbound traffic not explicitly allowed is dropped, **Severity**: Critical

### Step 4: Inbound Rule Matching Check

**Data Collection**:

> Collection target: Based on the user-reported blocked port, check whether matching enabled inbound rules exist, and whether there are explicit block rules

- PowerShell script: [networking-firewall.ps1](references/online/scripts/networking-firewall.ps1) Section Step 4

**Analysis Approach**:

1. Check whether matching allow rules exist (also verify whether the rule's Profile covers the current active profile):
   - Normal: Target port has enabled Allow rule, and the rule covers the current active profile
   - Abnormal: No matching allow rules, or rules exist but Profile does not cover the current active network type (e.g., rule only applies to Domain/Private, but current is Public) -> **Root cause**: No effective inbound allow rule in firewall, **Severity**: Critical

2. Check whether explicit block rules exist (rule priority: Block rules take priority over Allow rules):
   - Normal: No matching Block rules
   - Abnormal: Matching Block rules exist -> **Root cause**: Explicit Block rule overrides Allow rule (in Windows Firewall, Block rules always take priority over Allow rules), **Severity**: Critical

### Step 5: Outbound Rule Blocking Check

**Data Collection**:

> Collection target: Check default outbound policy and explicit outbound block rules, investigate the cause of application inability to connect to network

- PowerShell script: [networking-firewall.ps1](references/online/scripts/networking-firewall.ps1) Section Step 5

**Analysis Approach**:

1. Check default outbound action:
   - Normal: Default outbound action is Allow
   - Abnormal: Default outbound action is Block -> All outbound traffic not explicitly allowed is dropped; need to confirm whether corresponding outbound Allow rules exist

2. Check explicit outbound block rules:
   - Normal: No unreasonable outbound block rules
   - Abnormal: Outbound block rules with overly broad scope exist (e.g., blocking all TCP outbound) -> **Root cause**: Outbound block rule scope too broad, blocking normal traffic, **Severity**: Warning

### Step 6: Group Policy Firewall Rule Merge Check

**Data Collection**:

> Collection target: Check whether group policy manages firewall configuration, and whether local rule merge policy is effective

- PowerShell script: [networking-firewall.ps1](references/online/scripts/networking-firewall.ps1) Section Step 6

**Analysis Approach**:

1. Check whether group policy manages firewall:
   - Normal: No group policy firewall configuration, or group policy consistent with local configuration
   - Abnormal: Group policy has configured firewall but settings do not match expectations -> Need to confirm group policy source (domain controller or local)

2. Check local rule merge policy:
   - Normal: AllowLocalFirewallRules is True, local rules and group policy rules both effective
   - Information: AllowLocalFirewallRules is False -> Group policy prohibits local rule merge; locally created rules are not effective. This is a security policy design by the domain administrator and does not constitute a fault in itself. If the user reports that locally added rules are not effective, it means rules need to be deployed through group policy

3. Check whether group policy profile settings override local settings:
   - EnableFirewall, DefaultInboundAction and other settings in group policy will override local configuration
   - Abnormal: Group policy sets default inbound action to Block but does not deploy necessary allow rules -> **Root cause**: Group policy firewall configuration blocking inbound but missing necessary allow rules, **Severity**: Critical

If group policy managing firewall configuration is found, see -> [system-gpo.md](references/online/system-gpo.md)

### Step 7: WFP Packet Drop and Filter Rule Localization

> **Note**: WFP (Windows Filtering Platform) is the operating system's low-level network filtering framework, independent of the Windows Firewall service. Even if the firewall service is stopped or profiles are disabled, third-party software (such as antivirus, VPN, security hardening tools) can still inject filter rules through WFP to intercept traffic. Therefore, WFP checking **does not depend on firewall enable status**; as long as unexplained packet loss or intermittent network anomalies exist, this step should be executed.

**Data Collection**:

> Collection target: Export WFP network events and filter rules, used to analyze whether packet drop events related to the user's problem exist, and localize the specific filter rule causing the drops. WFP localization MUST be based on real packet drop event data; speculative conclusions without event evidence are prohibited

- PowerShell script: [networking-firewall.ps1](references/online/scripts/networking-firewall.ps1) Section Step 7
- **Two collection modes**:
  - Mode A Historical snapshot (`netsh wfp show netevents`): Exports netevents already recorded by the system, suitable for scenarios where the fault has occurred and events are still within the recording window
  - Mode B Collect immediately after fault reproduction: First reproduce the fault, then immediately execute Mode A's `netsh wfp show netevents`; the netevents circular buffer maintained by the system will contain recently occurred events. Suitable for reproducible fault scenarios, ensuring events are collected while still in the buffer

**Analysis Approach**:

**Step 1: Filter packet drop events from netevents.xml**

Read `netevents.xml`, filter events where `type` is `FWPM_NET_EVENT_TYPE_PUBLIC_CLASSIFY_DROP` (indicating the WFP classification engine dropped the packet). Extract the following fields from the `header` of each drop event:

| Field | Description |
|------|------|
| `localAddrV4` / `localAddrV6` | Local IP address |
| `remoteAddrV4` / `remoteAddrV6` | Remote IP address |
| `localPort` | Local port |
| `remotePort` | Remote port |
| `ipProtocol` | Protocol number (6=TCP, 17=UDP) |
| `appId` | Application path that triggered the traffic |
| `timeStamp` | Event occurrence time |

Extract `filterId` (the runtime ID of the filter that triggered the drop) from the `classifyDrop` node of the drop event.

Match related records in drop events based on the user's described problem symptoms (target port, target IP, protocol):
- Normal: No matching drop events -> WFP layer did not intercept the user's reported traffic
- Abnormal: Matching drop events exist -> Record the `filterId` from the event, proceed to Step 2 to localize the filter rule
- Abnormal: High-frequency drop events for the same target port/IP -> **Root cause**: WFP continuously dropping specific traffic, **Severity**: Warning

**Step 2: Localize the drop rule in filters.xml using filterId**

Search for the `filterId` obtained in Step 1 in `filters.xml`, locate the corresponding `<item>` node, and extract the following information:

| Field | Description |
|------|------|
| `displayData > name` | Filter rule name (usually corresponds to firewall rule name) |
| `displayData > description` | Filter rule description |
| `action > type` | Action type (`FWP_ACTION_BLOCK` indicates block) |
| `providerKey` | Provider GUID, used in Step 3 to localize the specific software source |
| `action > calloutKey` | Callout GUID (only present when action type is `FWP_ACTION_CALLOUT_*` series, used in Step 3 for callout query) |
| `filterCondition` | Filter conditions (IP, port, protocol, application and other matching conditions) |

Preliminarily determine the drop cause based on the rule name:
- Rule name contains Windows Firewall rule name (e.g., "Core Networking", user-created rule name) -> Drop caused by Windows Firewall rule, return to Step 4/5 to check corresponding rule
- `filterId` not found in `filters.xml` -> The filter has been deleted or is a temporary rule, source cannot be traced
- If need to confirm whether the rule is from third-party software -> Proceed to Step 3, localize the specific software through `providerKey`

**Step 3: Localize rule source based on providerKey / calloutKey**

Extract `providerKey` (provider GUID) from the filter rule obtained in Step 2, search for this GUID in the `<providers>` node of `filters.xml`, locate the corresponding provider entry, and extract:

| Field | Description |
|------|------|
| `displayData > name` | Provider name (e.g., "Microsoft Windows Filtering Platform", third-party software name) |
| `displayData > description` | Provider description, usually contains software vendor and usage information |
| `providerKey` | Provider GUID |

Determine the drop source based on provider information:

1. Provider name is "Microsoft Windows Filtering Platform" or `providerKey` is `{decc16ca-3f33-4346-be1e-8fb4ae0f3d62}` -> Drop caused by system default WFP policy
2. Provider name points to third-party software -> **Root cause**: Third-party software injected WFP filter rules causing traffic to be dropped, **Severity**: Warning. Obtain specific software name and vendor information from the provider's `displayData`
3. `providerKey` not found in `<providers>` -> Check whether the `action > calloutKey` extracted in Step 2 exists:
   - **calloutKey exists**: Search for this GUID in the `<callouts>` node of `filters.xml`, extract the callout's `displayData` (name/description) and `providerKey`. If the callout's `displayData` contains a clear third-party software or driver name -> Cross-reference with `Get-CimInstance Win32_SystemDriver | Select Name, DisplayName, PathName, State` to compare loaded kernel driver `.sys` paths to localize the source -> **Root cause**: Third-party driver intercepting traffic through callout, **Severity**: Warning. If the callout's `displayData` is empty or not matched in `<callouts>` -> Enter the pending verification process below
   - **No calloutKey**: Directly enter the pending verification process below
   - **Pending verification process**: Separate the confirmable facts (IP/port/protocol of drop events, filterId, filter/callout name) from the **speculation clearly marked "pending verification"** (possible sources inferred based on callout name, list of installed security software, list of loaded drivers, etc.) and present them to the user; attach user-side verification methods: clean boot (disable third-party services via msconfig then reproduce for comparison), disable/uninstall suspicious security software one by one then reproduce, or provide the complete `netsh wfp show state` file for expert analysis; update conclusions only after user verification feedback, do not write speculation directly as root cause

**Persistence scope determination (record before planning the fix)**: check the localized filter's `flags` in `filters.xml` -- `FWPM_FILTER_FLAG_PERSISTENT` or `FWPM_FILTER_FLAG_BOOTTIME` present -> the filter survives reboot and must be explicitly deleted; only `FWPM_FILTER_FLAG_INDEXED` (no persistence flags) -> the filter is session-scoped and disappears automatically when its owning provider's WFP session ends (this can make the fault look "self-healed" mid-diagnosis). Record which case applies and carry it into the fix plan, but note it never removes the need for an explicit, confirmed fix step: a session-scoped filter reappears whenever the injector re-runs, and "it may expire on its own" is not a substitute for deletion plus verification.

If the WFP filter points to third-party security software, see -> [security-malware.md](references/online/security-malware.md)

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Step 7 finds third-party WFP filter causing packet drops | -> [security-malware.md](references/online/security-malware.md) |
| Conditional jump | Step 3 finds network type anomaly requiring in-depth investigation | -> [networking-tcpip.md](references/online/networking-tcpip.md) |
| Conditional jump | Step 6 finds group policy managing firewall configuration | -> [system-gpo.md](references/online/system-gpo.md) |
| Chained successor | This file did not confirm root cause, user reports network connectivity issue | -> [networking-tcpip.md](references/online/networking-tcpip.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [networking-firewall.md](references/online/fixes/networking-firewall.md). Loading that file is MANDATORY before presenting any fix plan for a root cause confirmed here -- in particular, when Step 7 localizes a blocking WFP filter (third-party or injected), the fix MUST be taken from its "WFP third-party filter rules causing traffic drops" block (filter deletion recipe, verification, risk notes); improvising a self-authored deletion script (e.g. hand-written P/Invoke variants) is prohibited, because the tested recipe carries hard-won details (authentication service choice, engine-open failure modes) that memory or improvisation reliably gets wrong.
