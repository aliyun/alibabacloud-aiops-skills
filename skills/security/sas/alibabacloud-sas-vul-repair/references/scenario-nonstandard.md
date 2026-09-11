# Scenario 5: Manual Repair and Adaptation for Non-Standard Systems

This scenario addresses requests like "how do I fix vulnerabilities on self-compiled kernels, non-Alibaba-Cloud/other-cloud hosts, offline environments, custom images, or EOL systems": first judge the environment, then provide the adaptation path per the five branches, honestly state official limitations, and guide manual repair.

## Trigger Conditions

Example user phrasings (enter this scenario when any matches):

- "We use a self-compiled / modified kernel — one-click repair failed saying it's incompatible"
- "Our servers are on AWS/Tencent Cloud/an IDC — can vulnerabilities be fixed?"
- "Our environment has no public network access (isolated network) — how do we patch?"
- "Machines were batch-created from a custom image — how to handle the Agent and vulnerabilities?"
- "The system is already EOL (end of maintenance) — can vulnerabilities still be fixed? The repair button is grayed out"

## Prerequisites

1. CLI and credential checks, session-id generation: see SKILL.md. All API commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>`.
2. Manual repair commands must come primarily from the UpdateCmd/Solution returned by the API (real data); giving generic commands from experience alone is forbidden.
3. High-risk server-side operations in this scenario (kernel uninstallation, force fix, grub modification) require a snapshot and user confirmation first.

## Entry: Environment Judgment

Intent: read asset fields to determine which branch the user's environment belongs to, avoiding misuse of the standard repair flow.

```bash
aliyun sas describe-cloud-center-instances --criteria '[{"name":"internetIp","value":"<public-ip>"}]' --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Instance ID/instance name and other Criteria conditions can also locate the asset (more condition names in references/api-reference.md).

| Field | Judgment Purpose |
|---|---|
| `Vendor` | 0=Alibaba Cloud, 1=other clouds, 2=IDC → distinguishes Branch B |
| `OsName` / `Kernel` | OS and kernel version → judge self-compiled/non-standard kernels (Branch A), EOL systems (Branch E) |
| `AuthVersion` | 1 free, 3 enterprise, 5 advanced, 6 anti-virus, 7 ultimate → free edition has no repair capability (10=value-added service edition, only seen in describe-vul-list responses and describe-version-config's Version field) |
| `ClientStatus` | online/offline/pause → restore offline first (Branch C or install-agent) |
| `Flags` | Asset flag bits; auxiliary judgment of connection method and image origin (Branch D) |

Post-judgment routing: non-standard kernel → Branch A; Vendor not 0 → Branch B; network-restricted/offline → Branch C; image pre-installed → Branch D; EOL system → Branch E. Branches can stack (e.g., "AWS + offline"); when stacked, inform the user of both branches' limitations.

Five-branch overview table:

| Branch | Environment Feature | Key Limitation (must inform) | Main Path |
|---|---|---|---|
| A Self-compiled/non-standard kernel | Kernel is not the distribution standard version | Force fix skips compatibility validation with compatibility risk | Force fix (snapshot first) or manual kernel upgrade |
| B Non-Alibaba-Cloud/other clouds | Vendor=1/2 | Snapshot repair, rollback, and console reboot not supported | Back up on the source platform yourself + repair/manual repair |
| C Offline/isolated environment | No direct public network access | No official unified offline patch download channel | Proxy/dedicated-line connection; intranet repository; manual KB installation |
| D Custom image | Image pre-installed with Agent | Must shut down immediately after installation — never reboot | Dedicated installation-code flow + agentless detection review |
| E EOL system | System reached end of maintenance | No new patches; detection and repair no longer supported | Upgrade the OS; short-term ignore/whitelist |

## Branch A: Self-compiled / Non-standard Kernel

Background: when one-click repairing kernel vulnerabilities, Security Center validates the compatibility of the upgraded kernel with the client; if incompatible, repair is interrupted with a "target kernel incompatible" message.

Two handling paths (present the full pros/cons to the user, then let them choose):

| Path | Operation | Risks and Requirements |
|---|---|---|
| Path 1: Console force fix | Re-initiate repair with "force fix" checked, skipping the kernel-client compatibility validation | Compatibility risk (in severe cases the system cannot boot); **a snapshot must be created first**; prefer "auto-create snapshot and repair" |
| Path 2: Manual kernel upgrade | The user upgrades the kernel to the target version themselves, then returns to the console to verify | Requires a reboot window; upgrade steps vary by distribution — subject to official documentation |

Manual kernel upgrade example (Ubuntu):

```bash
apt-get update && apt-get install linux-image-<target-kernel-version>-generic
```

- After installation, reboot the server, confirm the running kernel switched to the target version with `uname -av`, then return to Security Center to trigger verification (vul_verify — see references/scenario-repair.md).
- CentOS/RHEL manual kernel upgrade approach (exact commands subject to official documentation): install kernel packages via yum or the official kernel-ml repository; after installation confirm the grub boot entry points to the new kernel (`grubby --default-kernel`), then reboot and verify.
- Check /boot space before upgrading (insufficient space triggers 8093 — see references/scenario-errors.md): `df -h /boot`.
- Related error codes: 8091 (qemu-booted kernel — submit an ECS ticket), 8094 (Signed kernel image cannot be upgraded — ignore or wait for expiry), 8095/8096 (vmlinuz/initramfs missing or kernel not in grub — uninstall and reinstall the kernel package; for 8096 a boot entry can be added with grubby) — see the kernel-class quick reference table in references/scenario-errors.md.
- Old kernel residue cleanup: same as references/scenario-recheck.md troubleshooting table item #8 (confirm running kernel → find old packages → snapshot → uninstall → ignore if still reported).

## Branch B: Non-Alibaba-Cloud / Other-Cloud Hosts (AWS Ubuntu etc.)

**Three official limitations (state honestly to the user first)**: non-Alibaba-Cloud servers do not support — ① snapshot repair; ② repair rollback; ③ the console "Reboot" button. A backup must be made on the source platform before repair; when a reboot is needed after repair, reboot it yourself.

Pre-repair backup advice (state clearly to the user):

| Source Platform | Backup Method |
|---|---|
| AWS | EBS snapshot (EC2 console → Snapshots) |
| Azure | Disk snapshot/image |
| Other clouds/IDC | Cloud platform snapshot capability or self-built backup |

None can be skipped: in one-click repair's "direct repair" mode there is no Security Center-side snapshot — problems cannot be rolled back, and the source-platform backup is the only safety net.

Repository issues (typical for AWS Ubuntu — all in references/scenario-errors.md):

- 8037: the host is configured with the Alibaba Cloud intranet repository mirrors.cloud.aliyuncs.com, which cannot be resolved in a public-network environment → switch to the public repository mirrors.aliyun.com (or replace it in /etc/yum.repos.d/).
- 9003: software is already the newest version but the vulnerability persists (the repository is not new enough or is not an Alibaba Cloud repository) → switch to the Alibaba Cloud repository and re-run repair.
- "Prefer Alibaba Cloud repository for vulnerability repair" can also be enabled in console Vulnerability Management Settings (operation in references/scenario-errors.md five-step troubleshooting Step 1).

Agent installation and network restrictions (multi-cloud intranet IP conflicts, unstable overseas networks, etc.):

- Point to the `alibabacloud-sas-install-agent` skill: non-Alibaba-Cloud machines install with VendorName=OTHER (connect via the public domain jsrv.aegis.aliyun.com); for network-restricted environments, proxy connection, dedicated-line connection, or specified server-domain connection are available — the detailed flow is provided by that skill.

Non-Alibaba-Cloud machine connection key points overview:

- The selection and specific configuration of connection methods (public direct connection, proxy, dedicated line, specified server domain — VendorName values, server-domain allow-listing, proxy specs and ports, etc.) are provided by the `alibabacloud-sas-install-agent` skill; this scenario does not expand on them.
- Risk summary: multi-cloud intranet IP conflicts and overseas network jitter are common root causes of Agent offline/installation failure; the troubleshooting approach interconnects with repair-failure network troubleshooting (see references/scenario-errors.md Step 4).

Agentless detection (alternative when the Agent cannot be installed):

- Snapshot/image-based isolated-environment scanning; supports AWS EC2, Azure, and other cloud platforms; installs no Agent and consumes no host resources; can serve as an alternative for vulnerability detection when the Agent cannot be installed (detection only — repair not included).
- Official documentation: https://help.aliyun.com/zh/security-center/user-guide/use-the-agentless-detection-feature (subject to the latest official version — retrieval method in references/doc-lookup.md).

## Branch C: Offline / Isolated Environment

Connection methods: environments without direct public network access connect to Security Center via proxy or Alibaba Cloud intranet dedicated line — installation and network configuration point to the `alibabacloud-sas-install-agent` skill.

Connection selection advice (explain to the user, then let them choose):

| Environment | Suggestion |
|---|---|
| Unified egress, many machines | Proxy connection (centralized ops, no per-machine public-network allow-listing) |
| Existing dedicated line/VPN | Dedicated-line connection (stable intranet channel) |
| Few machines with short-term public access | Public direct connection + whitelist-constrained allow-list |

Linux offline repair: repair depends on an accessible yum/apt repository. The repository can point to a self-built intranet mirror, but **the self-built repository's software versions must not be lower than the versions required by the vulnerability fix** (otherwise 8090 is triggered: the repository's highest version is below the vulnerability's required version — see references/scenario-errors.md).

Self-built intranet repository key points:

- Use tools like reposync to sync the Alibaba Cloud public repository (mirrors.aliyun.com) to an intranet HTTP service; keep periodic syncs to avoid falling behind on versions.
- The version required by the vulnerability fix can be obtained from vulnerability details (describe-vul-details / describe-vul-list's ExtendContentJson) — compare it against the highest version of the corresponding package in the self-built repository.
- The repair action is still dispatched by Security Center (requires the Agent online); only the repository points to the intranet.

Windows offline repair: manually download the corresponding KB patch from the Microsoft Update Catalog, upload it to the server and install; after installation, return to Security Center to trigger verification.

Environments where the Agent cannot be installed at all: use agentless detection (see Branch B) for vulnerability detection.

**State honestly (over-promising is forbidden)**: there is no official unified "offline vulnerability patch download" channel; the Linux offline solutions above (self-built intranet repository / manual installation) are derived from official manual repair cases — feasibility must be verified against the user's environment, and wording should leave room.

## Branch D: Custom Image

Precautions for images with pre-installed Agent (point to the `alibabacloud-sas-install-agent` skill for the full flow; this is the key risk warning):

1. When building the image template, you must use the **image-dedicated installation code** (OnlyImage=true distinguishes it from a normal installation code).
2. After running the installation command on the template machine: **shut down immediately after installation completes to create the image — NEVER reboot** — once rebooted, the client registers immediately and occupies that client ID.
3. Otherwise the client ID conflict prevents new instances created from that image from registering and coming online.
4. This flow must be repeated for every image rebuild (new installation code → install → shut down immediately → create image).

Flow diagram (full commands provided by the install-agent skill):

| Step | Action | Red Line |
|---|---|---|
| 1 | Create an image-dedicated installation code (OnlyImage=true) | Do not use a normal installation code |
| 2 | Run the installation command on the template machine | Do not reboot after execution |
| 3 | Stop/shut down immediately | Do not verify whether the Agent is online |
| 4 | Create the image at this state | — |
| 5 | After new instances boot, verify they come online | Repeat all steps for every image build |

Pre-release security review of the image: use agentless detection to scan the image once for vulnerabilities (see Branch B) — confirm the baseline is clean before batch-creating instances.

"Newly purchased ECS already has vulnerabilities" explanation phrasing: these are vulnerabilities of components bundled with the image (software version issues existing at image build time) — normal, not a new-machine intrusion; handle them through the normal vulnerability repair flow.

## Branch E: EOL (End-of-Life) Systems

- Vulnerabilities on EOL systems **require an OS upgrade to be fully fixed** — official repositories are offline and no new patches are released; this is also one of the official reasons for a "grayed-out repair button" (see references/scenario-errors.md Step 5 checklist).
- Newly disclosed vulnerabilities after EOL are no longer supported for detection and repair.
- The EOL list and schedule change dynamically — do not hardcode them in answers: obtain the latest version via the official overview document (overview-4 anchor) per references/doc-lookup.md.
- Commonly EOL or near-EOL systems (examples — subject to the official list): CentOS 7/8 (end of maintenance — migrate to Alibaba Cloud Linux/Anolis etc.), some old Ubuntu LTS versions, old Windows Server versions.
- Field-tested note (pitfall record): EOL systems do not necessarily show a "grayed-out repair button" — they may also manifest as **zero detections on both targeted and full scans**: the official side no longer releases patches, so image package versions compared against CVE advisories show no gap. Field-test case: a freshly installed Ubuntu 20.04 LTS (standard support ended 2025-05-31) showed 0 cve detections across multiple scan rounds; after reinstalling Alibaba Cloud Linux 3, the same machine immediately detected multiple vulnerabilities. When encountering "repeated zero-detection scans", beyond checking scan switches/scan target scope, prioritize checking whether the OsName is EOL.
- Selection advice for users (when stable detection/repair of vulnerabilities is needed): choose a distribution within its support period (e.g., Ubuntu 24.04, Alibaba Cloud Linux 3, Debian 12, Anolis 8), and use a **historical-version image** without running update after installation to stably produce detections; the latest images + fresh packages usually yield zero detections.
- Judgment method: compare the asset list's OsName against the official EOL list; or when the repair button is grayed out and disk/permission/service causes are ruled out, suspect EOL first.
- Mainstream alternative systems: Alibaba Cloud Linux, Anolis, Kylin V10, etc., are within Security Center's support scope (the support list changes dynamically — subject to official documentation).
- OS upgrade is a major change: advise the user to evaluate workload compatibility, back up with snapshots/images, then upgrade via the official migration solution.

## Common Misconceptions and Risk Warnings

| Misconception | Correction |
|---|---|
| "Non-Alibaba-Cloud machines can also use console one-click snapshot repair" | Not supported — you must back up on the source platform yourself before repair |
| "Force fix is much the same as normal repair" | Force fix skips compatibility validation and may prevent boot — a snapshot is mandatory first |
| "In offline environments, just download patch packages, copy them via USB, and install on the server" | There is no official unified offline patch channel; Linux requires an intranet repository (version-compliant) or manual package installation, Windows requires manual KB installation — feasibility must be verified |
| "Once the Agent is installed in the image, it can be used directly" | You must use the dedicated installation code and shut down immediately after installation; otherwise the client ID conflict prevents new instances from registering |
| "On EOL systems, upgrading a software version fixes vulnerabilities" | Official repositories are offline with no patches — a full fix requires an OS upgrade |
| "Agentless detection can also fix vulnerabilities" | Agentless detection is detection-only without repair — repair still requires the Agent online |

## Branch Stacking Scenario Examples

Real user environments often stack multiple branches; when stacked, limitations take the union and actions take the intersection:

| Stacked Scenario | Limitations to Inform the User | Recommended Path |
|---|---|---|
| AWS + self-compiled kernel | No snapshot/rollback/console reboot support + highest kernel compatibility risk | Source-platform backup → switch to public repository → manual kernel upgrade (skip force fix) |
| IDC offline + EOL system | No offline patch channel + no new patches | Plan an OS upgrade directly; short-term ignore for noise suppression |
| Custom image + non-Alibaba-Cloud | Image flow red lines + three official limitations | Build the image via the dedicated installation-code flow; after new machines come online, repair per Branch B |

## User Communication Key Points

- Limitation notification phrasing (mandatory for Branch B): "Non-Alibaba-Cloud servers do not support Security Center's snapshot repair, repair rollback, or console reboot. We strongly recommend making your own backup/snapshot on the source platform (e.g., the AWS console) before repair; when a reboot is needed, please handle it yourself."
- Force-fix risk phrasing (Branch A): "Force fix skips the kernel compatibility validation and carries compatibility risk — in extreme cases the system may not boot, so a snapshot is mandatory first. If your workload cannot accept this risk, we suggest the manual kernel upgrade path."
- Offline solution hedging phrasing (Branch C): "There is no dedicated offline patch download channel. What I'm providing is a solution compiled from official manual repair cases (intranet repository / manual KB installation) — feasibility needs verification against your environment."
- Image phrasing (Branch D): "For images with pre-installed Agent, be extremely careful: shut down immediately after installation to create the image — never reboot, or the client ID is occupied and none of the new machines can come online."
- EOL phrasing (Branch E): "After a system reaches end of maintenance, official repositories no longer release patches — fully fixing vulnerabilities requires an OS upgrade. Short-term, ignore/whitelist can control alert noise, but long-term we recommend planning a migration."
- Manual repair command principle: prefer citing the real data of UpdateCmd/Solution returned by the API; only when the API provides no command, give generic guidance and note "subject to your system's actual version".

## Notes and Boundaries

- **Environment judgment first**: for any non-standard scenario, run the entry environment-judgment command first — do not give solutions based solely on the user's verbal description.
- **State official limitations honestly**: Branch B's three limitations, Branch C's no offline patch channel, and Branch E's no patches available must be stated honestly — hiding limitations to facilitate repair is forbidden.
- **Double safety for high-risk operations**: operations like old kernel uninstallation, force fix, and grub modification require "snapshot first + user confirmation" double safeguards before guiding execution.
- **Boundary routing**: Agent installation, proxy/dedicated-line connection, and installation-code generation detailed flows belong to the `alibabacloud-sas-install-agent` skill — this scenario only provides risk warnings and routing, without expanding operation steps.
- Error code interpretation details are unified in references/scenario-errors.md; this scenario only lists branch-related error code indexes.
- Dynamic information like the EOL list and agentless detection supported platforms must be checked against the latest official documentation per references/doc-lookup.md before answering.
- When the pre-repair chain (edition/quota/Agent online/Windows prerequisite patches) is involved, still execute per references/scenario-repair.md's pre-fix chain — non-standard branches only change the "repair method choice" and never skip pre-checks.

## Related Documents

- Command parameters and response fields: [references/api-reference.md](api-reference.md)
- Official documentation dynamic retrieval (incl. EOL list/agentless detection): [references/doc-lookup.md](doc-lookup.md)
- Error code quick reference (kernel/repository classes): [references/scenario-errors.md](scenario-errors.md)
- Repair flow and manual repair path: [references/scenario-repair.md](scenario-repair.md)
- Old kernel residue cleanup and re-verification: [references/scenario-recheck.md](scenario-recheck.md)
- Scenario entry and boundary overview: [../SKILL.md](../SKILL.md)
