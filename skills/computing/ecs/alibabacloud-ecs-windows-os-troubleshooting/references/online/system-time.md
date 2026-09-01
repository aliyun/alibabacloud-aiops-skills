# System Time Diagnostics

## Function Description

Diagnoses Windows system time-related issues.

**Input**: User problem description (required), specific time deviation value (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| System time displays incorrectly, deviates from actual time | Step 1 (Time zone and DST) -> Step 2 (RealTimeIsUniversal) |
| System time deviation exactly equals the time zone offset (e.g., UTC+8 deviates by 8 hours) | Step 2 (RealTimeIsUniversal) |
| Time desync causing Kerberos authentication failure, SSL certificate validation errors | Step 3 (W32Time service) -> Step 4 (STS) -> Step 5 (NTP config) |
| Time service cannot start or sync fails | Step 3 (W32Time service) -> Step 5 (NTP config) |
| System time suddenly jumps by days/weeks/months | Step 4 (STS) |
| After time jump, w32tm /resync /rediscover cannot correct it, but recovers after initiating an SSL connection (e.g., visiting an HTTPS website) | Step 4 (STS) |
| Time reverts to incorrect after reboot | Step 1 (Time zone) -> Step 2 (RealTimeIsUniversal) |
| Time deviates by several hours immediately at boot (compared to host/actual time) | Step 2 (RealTimeIsUniversal, including boot time read event log evaluation) |
| Time deviation gradually increases after instance runs for a while (tens of seconds or more) | Step 3 (W32Time service + event log drift evaluation) -> Step 6 (Debug log) |
| Time gradually runs fast/slow, drifts back and forth, with no anomalies in config or logs (especially Server 2008) | Step 7 (Clock precision interference) |
| NTP sync persistently fails, w32tm /resync errors or times out | Step 3 (W32Time service) -> Step 6 (Debug log) |
| Time drift recurs repeatedly, deviates again shortly after sync | Step 3 (Event log) -> Step 6 (Debug log) -> Step 7 (Clock precision interference) |
| Need to verify NTP communication quality (latency/jitter/peer status) | Step 6 (Debug log) |

## Diagnostic Steps

### Step 1: Time Zone and Daylight Saving Time Configuration Check

**Data Collection**:

> Collection target: Obtain system time zone configuration, daylight saving time support status, and comparison of current local time with UTC time

- PowerShell script: [system-time.ps1](references/online/scripts/system-time.ps1) Section Step 1

**Analysis Approach**:

1. Check whether time zone configuration matches expectations:
   - Normal: Time zone matches user expectations (China instances typically use China Standard Time / UTC+8)
   - Abnormal: Time zone does not match expectations -> **Root cause**: Time zone configuration error, causing time display deviation, **Severity**: Warning

2. Check the offset between local time and UTC time:
   - Normal: Offset matches the time zone BaseUtcOffset
   - Abnormal: Offset does not match the time zone -> May be a RealTimeIsUniversal configuration issue, continue -> Step 2

3. Check daylight saving time status:
   - Normal: SupportsDaylightSavingTime=False (Daylight saving time is not used in China)
   - Informational: SupportsDaylightSavingTime=True and unexpected -> Daylight saving time being enabled may cause two time jumps per year

### Step 2: RealTimeIsUniversal Check

**Data Collection**:

> Collection target: Check the RealTimeIsUniversal value in the registry to determine how Windows interprets the hardware clock (UTC or local time)

- PowerShell script: [system-time.ps1](references/online/scripts/system-time.ps1) Section Step 2

**Analysis Approach**:

1. Check the RealTimeIsUniversal value:
   - Normal (virtualization environment): RealTimeIsUniversal=1, hardware clock interpreted as UTC, consistent with virtualization platform
   - Normal (physical machine + local time hardware clock): RealTimeIsUniversal=0 or does not exist
   - Abnormal (virtualization environment + current time already deviated): RealTimeIsUniversal=0 or does not exist, and system time deviation equals the time zone offset -> **Root cause**: In virtualization environment, hardware clock interpreted as local time, but host hardware clock is UTC, causing system time to deviate by one time zone offset, **Severity**: Critical
   - Risk (virtualization environment + current time normal): RealTimeIsUniversal=0 or does not exist, but current time displays normally (NTP has synced and corrected) -> **Root cause**: RealTimeIsUniversal not configured, current time is normal, but time deviation at the time zone offset level will recur before NTP sync completes after reboot, **Severity**: Warning
   - Note: RealTimeIsUniversal not existing is the Windows default state (equivalent to value 0); some custom images do not have this configured. Whether it needs to be fixed should be determined in conjunction with whether the current time is abnormal

2. Determine virtualization environment:
   - HypervisorPresent=True or Manufacturer contains virtualization identifiers (e.g., Alibaba Cloud, KVM, VMware) -> Virtualization environment, should set RealTimeIsUniversal=1
   - Physical machine environment -> RealTimeIsUniversal=0 is usually normal, but if using dual-boot (Windows + Linux), it should also be set to 1

3. Check the hardware clock time read at boot (event log evaluation):
   - At system boot, the kernel reads the initial time from the hardware clock (in virtualization, emulated by QEMU), recorded in the System log (ProviderName=Microsoft-Windows-Kernel-General, EventID=12, UTC format)
   - The hardware clock delivered by the virtualization platform is local time (without time zone information), and Windows interprets it according to the **current system time zone**: if the instance time zone does not match the expected time zone of the image/host (e.g., custom image using a non-UTC+8 time zone), the time read at boot will deviate by the corresponding time zone difference
   - Abnormal: The time recorded in EventID 12, when converted, deviates from the actual time by exactly the time zone offset -> Corroborates the RealTimeIsUniversal issue from evaluation 1, **Severity**: Critical
   - Collection command: `Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-General'; Id=12} -MaxEvents 5`

> If the time deviation exactly equals the time zone offset (e.g., UTC+8 environment deviates by 8 hours), it is almost certainly a RealTimeIsUniversal configuration issue.

> Alibaba Cloud ECS uses KVM virtualization, and the host hardware clock is UTC. Windows by default interprets the hardware clock as local time (RealTimeIsUniversal=0 or does not exist), and the hardware clock time read at startup is incorrectly treated as local time. If the W32Time service is running normally and NTP sync succeeds, the system time will be automatically corrected and display normally; however, after each reboot, before NTP sync completes, the time will deviate again. Therefore, even if the current time is normal, it is recommended to set RealTimeIsUniversal=1 in virtualization environments to fundamentally eliminate the deviation.

### Step 3: W32Time Service and NTP Sync Status Check

**Data Collection**:

> Collection target: Obtain W32Time service running status, NTP sync source, and sync status

- PowerShell script: [system-time.ps1](references/online/scripts/system-time.ps1) Section Step 3

**Analysis Approach**:

1. Check W32Time service status:
   - Normal: Service is running
   - Abnormal: Service is stopped -> **Root cause**: W32Time service not running, system time cannot auto-sync, **Severity**: Warning
   - Abnormal: Service startup type is Disabled -> **Root cause**: W32Time service disabled, time may continue to drift, **Severity**: Warning

2. Check NTP sync source:
   - Normal: Returns a valid NTP server address
   - Abnormal: Returns "Local CMOS Clock" -> **Root cause**: NTP server not configured, system uses local hardware clock, **Severity**: Warning
   - Abnormal: Returns empty or error -> NTP configuration abnormal, continue -> Step 5

3. Check NTP sync status (from w32tm /query /status output):
   - Normal: Last Successful Sync Time within a reasonable range (e.g., within 24 hours)
   - Abnormal: Last Successful Sync Time too long ago -> NTP sync may have failed
   - Abnormal: NtpServer is empty -> **Root cause**: NTP server not configured (NTPServerNotConfigured), **Severity**: Warning

4. Check time-related event logs (direct evidence of sync success/failure and drift):
   - Time-Service events (System log, ProviderName=Microsoft-Windows-Time-Service):
     - **EventID 35/37**: Time sync successful/corrected, presence of such events recently indicates the sync chain is normal
     - **EventID 36/47**: Sync failure/warning (signature verification failure, peer not responding, etc.) -> Combined with Step 5/6 to locate NTP chain issues
     - **EventID 50**: Local time deviates too much from NTP source (default exceeds 15 minutes), W32Time refuses automatic update, requires `w32tm /resync /rediscover` manual forced sync -> **Root cause**: Clock offset too large (LargeClockOffset), **Severity**: Warning
     - **EventID 134/135/139/143**: Time source/domain sync hierarchy abnormal, focus on domain environments
   - System uptime drift evaluation (System log, ProviderName=EventLog, EventID=6013):
     - This event records system Uptime (seconds) **once per hour**. The interval between two adjacent records should be 3600 seconds
     - Abnormal: Interval significantly deviates from 3600 seconds -> System clock is drifting (due to virtualization clock interrupt loss) or NTP sync is not effective -> **Severity**: Warning, continue -> Step 6 to verify sync quality
   - Time changed events (ProviderName=Microsoft-Windows-Kernel-General, EventID=1): Records who modified the system time, used to locate non-W32Time time tampering sources

> Alibaba Cloud ECS instances should be configured with Alibaba Cloud NTP servers (e.g., ntp.cloud.aliyuncs.com) by default. ECS Windows images have a default sync interval of 300 seconds (SpecialPollInterval=0x12c); if changed to the default value of 3600 seconds or larger, drift accumulation will be more noticeable.

### Step 4: Secure Time Seeding (STS) Check

**Data Collection**:

> Collection target: Check whether the Secure Time Seeding feature is enabled; this feature may cause system time to suddenly jump

- PowerShell script: [system-time.ps1](references/online/scripts/system-time.ps1) Section Step 4

**Analysis Approach**:

1. Check whether STS is enabled (UtilizeSslTimeData value):
   - Normal (cloud server / with reliable NTP): UtilizeSslTimeData=0, STS is disabled
   - Risk (cloud server): UtilizeSslTimeData=1 or does not exist (enabled by default), STS may cause the system clock to jump by days or even months based on erroneous time data from SSL/TLS handshakes, **Severity**: Critical

2. Check MaxPosPhaseCorrection / MaxNegPhaseCorrection (maximum positive/negative phase correction, in seconds):
   - Windows Server default 172800 seconds (48 hours), Windows client default 54000 seconds (15 hours)
   - Abnormal: Value too large (e.g., 0xFFFFFFFF = unlimited) -> Allows time jumps of any magnitude, extremely high risk
   - Abnormal: Value too small -> Normal NTP corrections may be rejected

3. Check event logs for time jump records:
   - Kernel-General Event ID 1: Records system time being changed; focus on whether the change reason is "An application or system component changed the time" and whether the source process is svchost.exe (hosting the W32Time service)
   - W32Time Operational Event ID 52/58/142: STS-calculated "Projected Secure Time" and "Target system time"; if there are significant deviation time jump records -> STS caused the time jump

4. Check SSL time cache values (SecureTimeLimits):
   - Read three values under `HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\SecureTimeLimits` (FILETIME format, convert with `[DateTime]::FromFileTime()`): SecureTimeEstimated (estimated value), SecureTimeHigh (upper bound), SecureTimeLow (lower bound)
   - Mechanism: Any server that establishes an SSL connection with this machine transmits time information to the client, and W32Time updates these three cache values accordingly; if the current system time deviates from the cache by more than +/-54000 seconds (15 hours), W32Time will **immediately** adjust the system time to SecureTimeEstimated
   - Key characteristic: **SSL time priority is higher than NTP time source**. If the time was jumped by STS, even if the NTP source is correct and the deviation does not exceed the maximum correction threshold, `w32tm /resync /rediscover` may not be able to correct it; only after initiating another SSL connection with correct time (e.g., visiting an HTTPS website) to refresh the cache will the time automatically recover
   - Evaluation: SecureTimeEstimated converted deviates significantly from current system time (days/months), and the user describes "forced sync ineffective, recovers after SSL connection" -> **Root cause**: Secure Time Seeding caused time jump (STSTimeJump), **Severity**: Critical
   - This key not existing is normal (STS disabled or SSL time not yet cached, common in Server 2012 R2 and earlier systems)

> **STS Mechanism Description**: Secure Time Seeding was introduced in Windows 10 1511 / Server 2016 and is enabled by default. This feature extracts ServerUnixTime and OCSP data from SSL/TLS handshakes and estimates the current time through heuristic algorithms. Its design purpose is to correct time without NTP when the CMOS battery is depleted and the system clock is severely deviated (breaking the circular dependency of "needing correct time to establish secure connections, and needing secure connections to obtain correct time").
>
> **Root Cause of STS-Induced Time Jumps**: Widely used TLS implementations such as OpenSSL have been filling the ServerUnixTime field with random values (non-specification server time) since 2014. STS misidentifies these random values as real time, calculates an erroneous "Projected Secure Time", and then jumps the system clock to the wrong time. The jump magnitude can reach days, weeks, or even months (forward or backward).
>
> **Microsoft Official Recommendation**: Microsoft published MC1085489 announcement in 2025, formally recommending disabling STS on Windows Server 2016/2019/2022/2025 (setting UtilizeSslTimeData=0), especially for servers already configured with reliable NTP time sources. Cloud servers (Alibaba Cloud ECS and other virtualization environments) already have reliable NTP services and MUST disable STS to avoid time jump risks.

### Step 5: NTP Server Registry Configuration Check

**Data Collection**:

> Collection target: Check NTP server configuration, sync type, and sync interval in the registry

- PowerShell script: [system-time.ps1](references/online/scripts/system-time.ps1) Section Step 5

**Analysis Approach**:

1. Check NTP server address:
   - Normal: NtpServer field is non-empty and contains valid server addresses
   - Abnormal: NtpServer is empty -> **Root cause**: NTP server not configured (NTPServerNotConfigured), **Severity**: Warning

2. Check time sync type:
   - Normal: Type is "NT5DS" (domain environment default, uses domain hierarchy sync) or "NTP" (standalone server)
   - Abnormal: Type is "NoSync" -> **Root cause**: Time sync disabled, system will not auto-sync time, **Severity**: Warning
   - Abnormal: Type is "AllSync" -> System uses all available sync mechanisms, usually normal but may cause instability

3. Check whether NTP client is enabled:
   - Normal: NtpClient Enabled=1
   - Abnormal: NtpClient Enabled=0 -> NTP client disabled, cannot sync from external NTP servers

4. Check NTP sync interval:
   - Normal: SpecialPollInterval is reasonable
   - Informational: SpecialPollInterval too large (e.g., >86400) -> Sync interval too long, time deviation may accumulate

> If you suspect the NTP server address comes from the metadata service, see -> [cloud-metaserver.md](references/online/cloud-metaserver.md) (Metadata NTP configuration check)

### Step 6: W32Time Debug Log In-Depth Analysis

**This step is an intrusive diagnostic operation and will not be automatically executed in the routine diagnostic flow.** Before executing, the following information MUST be explained to the user and explicit consent obtained:

1. **Operation details**: Will temporarily enable W32Time debug trace, force-trigger one NTP resync, and generate a ~5MB debug log file to `%SystemRoot%\Temp\w32time_diag.log`
2. **Potential impact**: `w32tm /resync /rediscover` will immediately trigger time sync; if the NTP source has significant deviation, the system time may jump, which may affect running time-sensitive applications (e.g., certificate validation, Kerberos authentication, database transactions)
3. **Recommended execution timing**: When Steps 1-5 are completed and the root cause of the time issue still cannot be identified
4. **Cleanup commitment**: After analysis is complete, the debug log file will be deleted and debug trace confirmed to be disabled

> Execute the following collection script only after the user explicitly replies with consent.

```powershell
# Enable w32time debug trace (temporary diagnostic probe)
$debugLog = "$env:SystemRoot\Temp\w32time_diag.log"
w32tm /debug /enable /file:$debugLog /size:5000000 /entries:0-300
# Trigger NTP resync to capture communication (async - returns immediately)
w32tm /resync /rediscover
# Wait for async NTP exchange to complete (DNS + packet round-trips)
Start-Sleep -Seconds 5
# Disable debug trace
w32tm /debug /disable
# Verify log file created
if (Test-Path $debugLog) {
  Write-Host "W32TIME_DEBUG_LOG=$debugLog"
} else {
  Write-Host 'DEBUG_LOG_NOT_FOUND'
}
```

- PowerShell script: [system-time.ps1](references/online/scripts/system-time.ps1) (Step 6 is an intrusive operation, not included in the script; must be executed separately after user consent)

**Analysis Approach**:

Log format: `{ThreadID} {Timestamp} - {Message}`. W32Time debug log is UTF-16 LE encoded; Select-String must specify `-Encoding Unicode`. Based on diagnostic needs, query the log file by dimension (extract only the needed dimension each time, do not output in full):

**1. DNS Resolution Status**:

```powershell
Select-String -Path "$env:SystemRoot\Temp\w32time_diag.log" -Pattern 'Retrying name resolution' -Encoding Unicode
```

- Occurrence of `Retrying name resolution for {peer} in {N} minutes` indicates the peer domain name cannot be resolved
- If **all** configured NTP peers fail to resolve -> **Root cause**: NTP peer DNS resolution failure (NtpDnsResolutionFailed), **Severity**: Critical
- If some peers fail to resolve but there are still available peers -> **Severity**: Warning

**2. Peer Reachability and Offset**:

```powershell
Select-String -Path "$env:SystemRoot\Temp\w32time_diag.log" -Pattern 'Response from peer' -Encoding Unicode
```

- Each line format: `Response from peer {name}, ofs: {offset}` -- reflects both peer reachability and clock offset
- If no `Response from peer` lines at all -> **Root cause**: NTP peer unreachable (NtpPeerUnreachable), **Severity**: Critical
- Offset evaluation: |offset| < 1ms normal; 1-128ms acceptable; >= 1s -> **Root cause**: Clock offset too large (LargeClockOffset), **Severity**: Critical
- Multiple peers with consistent offset direction (all positive/all negative) indicates systematic local clock deviation; mixed positive/negative with small range is normal jitter

**3. NTP Packet Quality**:

```powershell
Select-String -Path "$env:SystemRoot\Temp\w32time_diag.log" -Pattern 'Stratum:|RoundtripDelay:' -Encoding Unicode
```

- **Stratum**: 1=primary reference source, 2-15=secondary (normal), 16=not synchronized -> **Root cause**: NTP peer not synchronized (Stratum 16), **Severity**: Warning
- **RoundtripDelay**: <10ms normal (intra-cloud network); 10-100ms acceptable (WAN); >100ms abnormally high latency
- Intra-cloud NTP (100.100.x.x) latency is typically <5ms; significantly higher indicates network abnormality

**4. Intersection Algorithm and Sample Selection**:

```powershell
Select-String -Path "$env:SystemRoot\Temp\w32time_diag.log" -Pattern 'Intersection successful|Discarding Sample|NTP Sample.*chosen' -Encoding Unicode
```

- `Intersection successful` -> Algorithm successfully filtered a trusted time range
- `Discarding Sample with offset:` -> Outlier sample discarded (small amounts are normal)
- `NTP Sample {id} chosen. Dispersion: {val}` -> Final selected sample; smaller Dispersion is better, >8s indicates low sample quality

**5. Clock Discipline and State Transitions**:

```powershell
Select-String -Path "$env:SystemRoot\Temp\w32time_diag.log" -Pattern 'ClockDispln Discipline:|Unset->|Time Slip Notification|reliable time service with no time source' -Encoding Unicode
```

- `ClockDispln Discipline: *SKEW*TIME*`: `PhCRR` absolute value gradually decreasing = converging; `KPhO` absolute value continuously increasing = clock diverging
- `Unset->Hold` -> Clock discipline initialization (normal startup behavior)
- `Time Slip Notification` -> Forced resync requested
- `reliable time service with no time source` -> System has no valid time source; combine with dimensions 1/2 to determine root cause

> **Comprehensive Analysis Guide**: First check dimension 2 (whether there are peer responses), then check dimension 1 (whether DNS failed), then check offset and latency (dimensions 2/3), and finally analyze clock discipline state (dimension 5). You do not need to query all dimensions every time; decide whether to go deeper based on preceding analysis results.
>
> **Tx/Rx Timestamp Warning** (`Tx timestamp not returned`) is common in cloud server environments and does not affect NTP sync functionality; can be ignored.

**Data Cleanup**:

> Remove the debug log file after analysis is complete:

```powershell
Remove-Item "$env:SystemRoot\Temp\w32time_diag.log" -Force -ErrorAction SilentlyContinue
```

### Step 7: Clock Precision Interference Check (timeBeginPeriod)

**Data Collection**:

> Collection target: Confirm OS version (Server 2008 is high-incidence), confirm cloud assistant agent service status (legacy golang implementation is a known interference source). The actual caller of timeBeginPeriod cannot be located via script (winmm API calls have no observation surface, process name matching does not constitute valid evidence), and is not within the collection scope

- PowerShell script: [system-time.ps1](references/online/scripts/system-time.ps1) Section Step 7

**Analysis Approach**:

1. Applicable symptom screening (confirm symptoms match before executing this step):
   - Typical symptoms: System time **gradually** runs fast or slow, drifts back and forth (not a one-time jump), and Steps 1-6 find no anomalies (NTP sync successful, no STS jump records, configuration normal)
   - Historical cases are concentrated on **Windows Server 2008**; other versions may also be affected if processes frequently calling timeBeginPeriod exist

2. Check OS version:
   - Windows Server 2008/2008 R2 (Version 6.0/6.1) -> High risk, primary suspicion for this root cause
   - Other versions -> Lower probability, but still need to manually locate the caller per step 3

3. Locate the caller (all executed manually by the user, not covered by the script; process name matching does not constitute valid evidence):
   - Background mechanism: Programs using the golang runtime, when using timers/`time.Sleep`, call timeBeginPeriod/timeEndPeriod to switch system clock precision on entering/exiting idle; on Server 2008 this behavior causes clock precision to drift back and forth, which in turn causes system time to run fast/slow (see golang/go#24489). Known case: the cloud assistant agent's legacy golang implementation called timeBeginPeriod approximately 4 times per second, which has been fixed by the official team via API hook; upgrading to the latest version resolves it
   - Verification methods (must be executed manually by the user):
     - Use the CheckTimeBeginPeriod tool to directly locate the process calling timeBeginPeriod (the process printed by the tool console is the caller):
       - Download URL: `https://changqu.oss-cn-hangzhou.aliyuncs.com/CheckTimeBeginPeriod.zip` (auxiliary diagnostic tool implemented via API hook; run the exe directly after extraction)
       - Note: This tool is not an official component and is an API hook-type program; it may be blocked by some security software. Please remind users to assess on their own; if the link is invalid, fall back to the stop-and-observe method below
     - Temporarily stop the suspected program (e.g., cloud assistant) and observe whether time returns to normal: if drift stops after stopping -> confirms the program is the interference source

4. Root cause determination:
   - Time returns to normal after stopping the suspected process, or a process is detected calling timeBeginPeriod at high frequency -> **Root cause**: Clock precision interference (ClockPrecisionInterference, caller process frequently modifying system clock precision causing time drift), **Severity**: Warning
   - Note: This type of issue is unrelated to NTP; `w32tm /resync` only provides temporary correction, and drift will continue; the interference source MUST be eliminated

> **Mechanism Description**: The system default clock precision is 15.6ms (approximately 64 clock interrupts per second), and the system relies on accumulating clock interrupt counts to maintain time. When a process calls `timeBeginPeriod`, it raises the clock precision to a higher frequency; frequent switching between high and low precision (e.g., golang runtime entering/exiting idle) causes systematic errors in clock counting, manifested as time gradually running fast or slow. In virtualization environments, clock interrupts themselves have scheduling overhead, and the drift is more noticeable when compounded.

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | NTP server points to metadata configuration | -> [cloud-metaserver.md](references/online/cloud-metaserver.md) (Metadata NTP check) |
| Conditional jump | Time deviation affects Kerberos authentication | -> [identity-auth.md](references/online/identity-auth.md) (Kerberos clock skew) |
| Conditional jump | Debug log shows NTP peer DNS resolution failure | -> [networking-dns.md](references/online/networking-dns.md) (DNS resolution troubleshooting) |
| Conditional jump | Debug log shows NTP peer unreachable (UDP 123 no response) | -> [networking-firewall.md](references/online/networking-firewall.md) (Check outbound UDP 123 port rules) |
| Conditional jump | Step 7 confirms cloud assistant agent as clock precision interference source | -> [system-management.md](references/online/system-management.md) (Cloud assistant status and upgrade) |
| Chain successor | Root cause not confirmed in this file, user reports cloud platform-related issue | -> [cloud-metaserver.md](references/online/cloud-metaserver.md) |


## Fix Recommendations

Fix solutions for root causes confirmed in this file are found in [system-time.md](references/online/fixes/system-time.md).
