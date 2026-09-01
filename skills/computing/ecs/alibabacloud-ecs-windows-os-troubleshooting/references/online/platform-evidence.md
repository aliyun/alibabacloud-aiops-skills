# Platform-Side Evidence (Online + Offline)

## Function Description

When diagnosis runs over the remote execution channel, the aliyun CLI can read platform-side data -- instance metadata, security-group rules, disk metadata, monitoring metrics, system events, console screenshots. The platform sees the instance from the virtualization layer; the GuestOS sees itself from inside. Comparing the two views corroborates in-instance findings, bounds them (e.g., traffic pinned at a spec cap), exposes discrepancies that are themselves diagnostic clues -- and sometimes the platform view alone fully explains the user's symptom, making a GuestOS deep-dive pointless. This file defines when and how platform-side data plays each of those roles.

Platform data is organized into three roles with different authority:

| Level | Role | When | Authority |
| --- | --- | --- | --- |
| **L1 Platform Context Snapshot** | Capture platform facts about the diagnosis target | Always, on the mandatory prerequisite `describe-instances` call | Record as session context; never a conclusion by itself |
| **L2 Platform Triage** | Decide whether platform-side facts fully explain the symptom | After problem classification, before the domain deep-dive; remote channel only | MAY conclude a platform-side root cause and exit the GuestOS deep-dive, under the exit gates below |
| **L3 Cross-Validation** | Corroborate, bound, or timestamp in-instance findings | During/after in-instance collection; remote channel only | Auxiliary only -- never replaces in-instance collection, never changes domain classification |

**Scope constraints (MUST observe)**:

1. **Remote execution channel only**: these are OpenAPI calls made from the machine running the aliyun CLI. In direct execution channel mode (agent inside the GuestOS), skip platform-side collection entirely; do not ask the user to install/configure the CLI just for platform evidence.
2. **Read-only discipline**: every API in this file is a read-only Describe/Get action. This skill never calls platform write APIs (no bandwidth change, no security-group edit, no EIP bind) -- platform-side remediation is presented to the user as console/API guidance, never executed by the skill.
3. **Graceful degradation**: any platform call that fails (missing RAM action, unsupported instance family, throttling) is recorded as "platform-side data unavailable: {reason}" and MUST NOT block or abort the GuestOS diagnostic sequence.
4. **Per-domain triggering**: fetch only the APIs mapped to the current problem domain group; do not pull everything for every case.

## L1: Platform Context Snapshot

The remote-channel prerequisites already mandate one `aliyun ecs describe-instances` call (Status + OSType gate). That response carries far more than the two gated fields -- capture the rest into session context beside `RegionId` / `InstanceId` / session-id, at zero extra API cost. Later steps (L2 triage, Evidence Review) read from this snapshot instead of re-calling the API.

**Fields to capture**:

| Field | Value for diagnosis |
| --- | --- |
| `Status`, `OSType` | Already gated by prerequisites |
| `InstanceType` (+ CPU/memory) | Spec caps for throttling judgments (bandwidth, PPS, baseline CPU for burstable families); the single source of truth for "is the instance hitting its spec limit"; input to the NVMe applicability gate ([driver.md](references/offline/driver.md) Step 6.0) |
| `ImageId` | Input to the NVMe applicability gate ([driver.md](references/offline/driver.md) Step 6.0, `describe-images` Features.NvmeSupport) |
| `PublicIpAddress`, `EipAddress` | Whether the instance has a public entry/exit point at all -- the first question behind every "cannot reach public internet / cannot reach the instance from outside" symptom |
| `InternetMaxBandwidthOut` / `InternetMaxBandwidthIn` | Zero outbound bandwidth means public egress is impossible regardless of GuestOS state |
| `SecurityGroupIds` | Key for the L2 security-group rule check |
| `VpcAttributes` (VSwitchId, private IP) | Which network plane the instance is actually on; needed to interpret in-guest IP findings |
| `ZoneId` | Context for zone-scoped platform events |
| `CreationTime` / `StartTime` | Boot-time anchor for time-window consistency checks in the causal chain |

The snapshot records facts; it never concludes by itself -- conclusions are drawn only in L2/L3 under the rules below.

## L2: Platform Triage

**Purpose**: before spending round trips on a GuestOS deep-dive, check whether platform-side facts already fully explain the user's symptom. Some symptoms that feel like GuestOS faults ("cannot reach the internet", "RDP times out", "instance rebooted overnight") are entirely decided outside the GuestOS; diagnosing the guest for them produces confident-looking work with no possible fix. Triage exists to catch those early -- and only those.

**Trigger**: remote channel active, problem classified, L1 snapshot in session context. Consult the per-domain mapping below; execute at most 1-2 additional read-only calls beyond the snapshot, then judge.

**Exit gates (MUST all hold before concluding a platform-side root cause and stopping the GuestOS deep-dive)**:

1. **Full explanation**: the platform fact(s) explain ALL user-reported symptoms, not just part of them. A platform fact that explains only some symptoms is a finding, not an exit -- continue the GuestOS sequence for the rest.
2. **No contradicting in-instance evidence**: data already collected in-guest must not conflict with the platform conclusion. A genuine conflict keeps both observations and continues diagnosis (present the discrepancy in the Evidence Review).
3. **Evidence traceability**: the conclusion goes through the Evidence Review with every platform fact labeled **platform-side**, citing the exact API and field values.
4. **Incidental in-guest anomalies are not dropped**: configuration anomalies already observed inside the guest (e.g., DHCP disabled on an adapter that ECS expects to be DHCP-managed) are reported as separate findings even when the primary root cause is platform-side, with a confirmation request on whether to fix them alongside the platform remediation. Silent omission is a diagnostic miss, not a clean exit.

**After a platform-root-cause exit**: output the conclusion per the WORKFLOW-GUIDE output templates, with platform remediation presented as user-side console/API guidance (never executed by this skill), incidental in-guest findings listed separately, and no GuestOS fix script for the platform root cause itself.

### Per-Domain Triage Mapping

| Domain group | Platform check (from L1 snapshot or 1-2 extra calls) | Abnormal -> platform-side root cause |
| --- | --- | --- |
| InsideNetworkAccessFailed -- public targets unreachable | Snapshot: `PublicIpAddress` / `EipAddress` / `InternetMaxBandwidthOut` | No public IP/EIP, or outbound bandwidth = 0 -> public egress is impossible at platform level. Note the boundary: this explains "public unreachable" only; if in-guest data shows VPC-internal connectivity also broken, the GuestOS sequence MUST continue |
| OutsideNetworkAccessFailed / RDPConnectingFailed / SMBAccessFailed (from outside) | Snapshot: public entry + `describe-security-group-attribute` (ingress rules for the target port: 3389 / 445 / business port) | No public entry point, or no ingress rule allowing the target port -> unreachable at platform level. An explicit `Drop` rule on the port is direct evidence |
| Network / disk performance below expectation | Snapshot `InstanceType` + `describe-instance-monitor-data` / `describe-disk-monitor-data` over the fault window, compared against the instance-type / disk-PL caps | Traffic or IOPS pinned at the spec cap across the fault window -> spec throttling, not a GuestOS fault |
| Crash / Hang / unexpected reboot / lifecycle anomaly | `describe-instance-history-events` aligned with the user-reported fault time | Maintenance / live-migration / host-failure / system-reboot events coinciding with the symptom window -> platform-initiated event; in-guest crash analysis proceeds only if events are absent or non-correlated |
| Startup stuck ("Starting", management side) | Snapshot `Status` + history events + `get-instance-screenshot` | Lifecycle stalled before OS hand-off -> platform-side boundary (already the routing table's management-side determination; platform data is its evidence) |
| AttachOrDetachDiskFailed | `aliyun ecs describe-disks --biz-region-id <region-id> --disk-ids '["<disk-id>"]'` for the involved disk: `Status` / `Category` / attachment | Platform-side disk stuck in `Attaching` / `Detaching`, or attachment state inconsistent with the in-guest view -> platform-side handling; GuestOS driver diagnosis continues only when the platform state is clean |

**Interpretation discipline**: absence of a platform-side anomaly is itself a finding ("public entry present, security group allows 3389 -> the cause is in-guest") and MUST be stated in the Check Item Summary so the user sees what was ruled out and why the diagnosis goes deeper. Never skip silently into the GuestOS sequence.

## L3: Cross-Validation

Platform data fetched alongside in-instance collection corroborates, bounds, or timestamps in-instance findings. It never replaces intra-instance collection and never changes problem domain classification. When platform data and in-instance data conflict, first consider measurement-layer and aggregation differences, then keep both views and present the discrepancy honestly in the Evidence Review.

### API Mapping by Problem Domain Group

| Domain Group | CLI (plugin mode) | Data Returned | Cross-Validation Value |
| --- | --- | --- | --- |
| Performance (CPU) | `aliyun ecs describe-instance-monitor-data --region <region-id> --instance-id <id> --start-time <iso8601> --end-time <iso8601>` | Sampled CPU utilization, internal/public network BPS and PPS | Whether high CPU observed in-instance is also visible platform-side, and whether the time profile matches the user-reported fault window |
| Network | `aliyun ecs describe-instance-monitor-data` (same parameters) | Network BPS/PPS samples | Whether packet loss / slowdown coincides with bandwidth or PPS saturation (spec throttling) versus a GuestOS configuration issue |
| Storage / disk performance | `aliyun ecs describe-disk-monitor-data --region <region-id> --disk-id <disk-id> --start-time <iso8601> --end-time <iso8601>` | Per-disk IOPS, BPS, latency | Whether slow disk I/O is cloud-disk throttling (approaching the disk performance-level limits) versus a GuestOS-level issue (filter driver, queue depth) |
| All domains (event correlation) | `aliyun ecs describe-instance-history-events --biz-region-id <region-id> --instance-id <id>` | System events: maintenance, live migration, host errors | Whether a platform event coincides with the fault time -- turns "sudden unexplained fault" into a correlated finding |
| VNC / screen state | `aliyun ecs get-instance-screenshot --biz-region-id <region-id> --instance-id <id>` | Console screenshot (Base64-encoded JPEG) | Cross-check the actual screen state for VNC black screen / unresponsive-screen cases without asking the user for a manual screenshot |

Note: the two monitor-data subcommands take the global `--region` endpoint override (they have no region request parameter and reject `--biz-region-id`); the others take `--biz-region-id`. Flag spellings were verified with `aliyun-cli-ecs 0.7.8` -- see the CLI flag reference in [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md) Section CLI Flag Reference, and check `aliyun ecs <subcommand> --help` when a flag is rejected.

**Memory note**: instance basic monitoring does not provide memory utilization -- do not chase platform-side memory data; rely on in-instance memory collection in the performance domain files.

### GetInstanceScreenshot Usage Notes

- The instance MUST be in Running state; instances created before 2018-01-01 and retired instance families do not support the API
- The response `Screenshot` field is a Base64-encoded JPEG: decode it to a file and view the image directly (e.g., `base64 -d` or PowerShell `[IO.File]::WriteAllBytes('<path>', [Convert]::FromBase64String('<b64>'))`)
- The screenshot is screen-state cross-validation evidence only
- **All-black capture caution**: a VNC console with no attached session usually yields an all-black screenshot -- a capture artifact, not necessarily a genuine "no output" boot scene. Never conclude a P1 boot-chain failure from an all-black capture alone: cross-check the capture timestamp against the reported fault window, the instance status, and the event log (last event timestamp / BugCheck) before treating it as boot evidence; if still ambiguous, recapture after a console restart and observe the boot attempt
- If the call fails (unsupported instance, permission), fall back to asking the user for a console screenshot -- do not block the main diagnostic sequence on it

## Offline Applicability

Platform evidence in offline diagnosis follows the **object-alignment principle: platform data is valid only for the object actually being diagnosed**. Offline work has two shapes, and they differ decisively:

| Offline shape | Diagnosis target | Platform data applicability |
| --- | --- | --- |
| **A. Rescue environment on the original instance** (e.g., rescue PE booted on the faulty instance itself; commands still reach that instance) | The original instance | Instance-scoped platform data describes the faulty machine itself -> L1 snapshot, L2 triage, and L3 cross-validation all apply exactly as in online mode |
| **B. Faulty system disk mounted as a data disk on a different helper instance** | The disk, NOT the helper instance | ONLY disk-scoped platform data aligned by DiskId is valid; the helper instance's platform context is irrelevant to the fault |

**Shape B red line**: the helper instance's `describe-instances` context (its public IP, security groups, monitor data, history events) says nothing about the faulty machine -- projecting any of it into the diagnosis is forbidden. The helper appears in this flow only as the machine executing commands; its Status/OSType check remains mandatory for the remote channel (that is a channel prerequisite, not a diagnostic finding about the fault).

**Disk-scoped platform data available in shape B**:

| Data | CLI | Use |
| --- | --- | --- |
| Disk metadata: `Status` / `Category` / `Size` / attachment | `aliyun ecs describe-disks --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-windows-os-troubleshooting/{session-id} --biz-region-id <region-id> --disk-ids '["<disk-id>"]'` -- the DiskId of the mounted faulty disk; an unfiltered call (account-wide disk inventory) is prohibited | Confirms the disk itself is platform-healthy and attached; a disk stuck in an abnormal platform state is a platform-side finding, not a GuestOS one |
| Disk events | `describe-instance-history-events` filtered to disk-level event types (`Disk:ErrorDetected`, `Disk:Stalled`, etc.) against the faulty disk | Correlates the fault window with platform-detected disk errors. Instance-level events are excluded here -- they belong to the helper, not the fault |
| Disk monitor data | `describe-disk-monitor-data` | Reflects only the current mount period on the helper instance; useful to rule out helper-side IO interference, never to infer the original fault |

If the source instance still exists and its ID is known, its metadata/history MAY be queried as background context (it often has been released -- a failed lookup is expected and MUST NOT block).

## Execution Rules

1. Reuse the session context (`RegionId`, `InstanceId`, session-id) and the UA rules of [REMOTE-EXECUTION.md](references/REMOTE-EXECUTION.md) Section Observability for every call; these are read-only OpenAPI calls and do not involve Cloud Assistant
2. Time window: align `--start-time`/`--end-time` (ISO 8601) with the user-reported fault window; when the fault time is unknown, use the last 1-3 hours. Note that monitoring data has platform-side sampling granularity -- a short spike may not appear in platform samples, so absence of a platform-side spike does not refute an in-instance observation
3. Interpretation discipline: platform metrics are measured at the virtualization/cloud-disk layer with their own aggregation windows; when the two views disagree, first consider measurement layer and aggregation differences, then treat genuine discrepancies as clues (e.g., platform bandwidth pinned at the instance spec cap -> spec throttling, not a GuestOS fault)
4. Output: platform findings enter the Evidence Review as evidence items labeled **platform-side**, cross-checked against in-instance items labeled **in-instance**; conclusions supported by only one view MUST keep that limitation visible

## Cross-References

- REMOTE-EXECUTION reference -- remote channel mechanics, UA template and session-id rules, CLI flag reference
- RAM policies reference -- RAM actions required by these APIs
- Online WORKFLOW-GUIDE "Path Planning" platform-side triage step and "Step-by-Step Execution" rule 7 -- where L2/L3 are invoked
- Offline WORKFLOW-GUIDE "Platform-Side Data" section -- where the offline shape determination happens
