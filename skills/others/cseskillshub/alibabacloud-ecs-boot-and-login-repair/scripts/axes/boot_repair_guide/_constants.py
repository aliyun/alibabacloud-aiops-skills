"""Static constants for alibabacloud-ecs-boot-repair-guide.

Everything the entry script knows about boot-failure triage lives here as code constants.
No data files are shipped under ``scripts/`` (package rule 1.1.2): tables that used to be
JSON live in this module instead.

Knowledge provenance: the categories, error strings, and handoff rules encode the reviewed
support practice for this tier plus the ECS help-center articles listed in
``references/doc-sources.md``. Strings that could not be sourced were left out rather than
invented; ``UNKNOWN`` handling in the entry script is therefore expected, not exceptional.
"""

SKILL_NAME = "alibabacloud-ecs-boot-repair-guide"

# Observability: one session id per script run, reused on every cloud call.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}"

# CLI transport
ALIYUN_BIN = "aliyun"
CLI_TIMEOUT_SECONDS = 60
CLI_RETRIES = 3
RETRY_BACKOFF_BASE_SECONDS = 1.0
RETRYABLE_CODES = frozenset({
    "Throttling", "ThrottlingUser", "RequestTimeout", "ServiceUnavailable",
    "InternalError", "SDK.ServerUnreachable", "ReadTimeout", "Timeout",
})

# Product / API versions actually used.
PRODUCT_ECS = "ecs"
PRODUCT_STS = "sts"
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"

# ---------------------------------------------------------------------------
# Cloud API allowlist. Any action not in this mapping is refused by _cli.py.
# ---------------------------------------------------------------------------
ALLOWED_ACTIONS = {
    "DescribeInstances": (PRODUCT_ECS, ECS_API_VERSION),
    "DescribeInstanceStatus": (PRODUCT_ECS, ECS_API_VERSION),
    "DescribeAvailableResource": (PRODUCT_ECS, ECS_API_VERSION),
    "DescribeInvocations": (PRODUCT_ECS, ECS_API_VERSION),
    "DescribeDisks": (PRODUCT_ECS, ECS_API_VERSION),
    "DescribeSnapshots": (PRODUCT_ECS, ECS_API_VERSION),
    "GetCallerIdentity": (PRODUCT_STS, STS_API_VERSION),
}

# Verb prefixes that mark a change-level API. Kept for the guard message only: the
# allowlist above is the enforcement, this list explains a refusal.
CHANGE_VERB_PREFIXES = (
    "Create", "Modify", "Delete", "Release", "Reset", "Replace", "Attach", "Detach",
    "Rebind", "Import", "Revoke", "Bind", "Unbind", "ReInit", "Reboot", "Start",
    "Stop", "Put", "Authorize", "Run", "Invoke", "Remove", "Uninstall", "Install",
)

# ---------------------------------------------------------------------------
# Result contract
# ---------------------------------------------------------------------------
STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

# ---------------------------------------------------------------------------
# Triage branches. `gate` values: in-scope | handoff | unknown.
# ---------------------------------------------------------------------------
BRANCHES = {
    "grub-loader": {
        "label": "Boot loader / GRUB configuration damage",
        "gate": "in-scope",
        "layer": "boot loader stage, before the kernel",
        "reference": "references/grub-efi-repair-guidance.md",
        "os_family": "linux",
    },
    "efi-boot-entry": {
        "label": "EFI boot entry or fallback path inconsistent with the installed loader",
        "gate": "in-scope",
        "layer": "firmware boot selection",
        "reference": "references/grub-efi-repair-guidance.md",
        "os_family": "linux",
    },
    "boot-files-lost": {
        "label": "Boot or system content missing (volume readable, files gone)",
        "gate": "in-scope",
        "layer": "volume contents",
        "reference": "references/data-rescue-and-reinstall.md",
        "os_family": "any",
    },
    "fstab-mount": {
        "label": "Mount table names a device or type that no longer resolves",
        "gate": "in-scope",
        "layer": "startup mount stage",
        "reference": "references/fstab-and-devices.md",
        "os_family": "linux",
    },
    "filesystem-state": {
        "label": "Volume remounted read-only after recorded errors, or integrity check failed at startup",
        "gate": "in-scope",
        "layer": "kernel mount stage",
        "reference": "references/evidence-checklist.md",
        "os_family": "linux",
    },
    "post-update-normal": {
        "label": "Long but progressing first boot after an update",
        "gate": "in-scope",
        "layer": "update completion, not a fault",
        "reference": "references/post-update-boot-failure.md",
        "os_family": "any",
    },
    "post-update-kernel": {
        "label": "Kernel or distribution upgrade left the loader and startup image inconsistent",
        "gate": "in-scope",
        "layer": "boot loader stage after a package transaction",
        "reference": "references/post-update-boot-failure.md",
        "os_family": "linux",
    },
    "windows-bsod": {
        "label": "Windows start-time crash (bugcheck)",
        "gate": "in-scope",
        "layer": "kernel start",
        "reference": "references/windows-bsod-triage.md",
        "os_family": "windows",
    },
    "handoff-capacity": {
        "label": "Disk capacity or inode exhaustion",
        "gate": "handoff",
        "layer": "capacity axis",
        "reference": "references/handoff-map.md",
        "target_skill": "the disk capacity skill",
        "os_family": "any",
    },
    "handoff-expansion": {
        "label": "Partition or expansion problem, including GUID conversion and LVM damage",
        "gate": "handoff",
        "layer": "expansion axis",
        "reference": "references/handoff-map.md",
        "target_skill": "alibabacloud-ecs-disk-expand-diagnosis",
        "os_family": "any",
    },
    "handoff-instance-state": {
        "label": "Instance parked in Starting or Stopping after a change",
        "gate": "handoff",
        "layer": "control-plane axis",
        "reference": "references/handoff-map.md",
        "target_skill": "alibabacloud-ecs-instance-state-diagnosis",
        "os_family": "any",
    },
    "handoff-io": {
        "label": "Saturated disk IO or memory pressure masquerading as a boot failure",
        "gate": "handoff",
        "layer": "performance axis",
        "reference": "references/handoff-map.md",
        "target_skill": "alibabacloud-ecs-disk-io-diagnosis",
        "os_family": "any",
    },
    "handoff-patch": {
        "label": "Patch or vulnerability installation action failed while the OS still boots",
        "gate": "handoff",
        "layer": "patch axis",
        "reference": "references/handoff-map.md",
        "target_skill": "alibabacloud-ecs-patch-management",
        "os_family": "any",
    },
    "handoff-connection": {
        "label": "The OS is up; the remote-login path is what fails",
        "gate": "handoff",
        "layer": "connection axis",
        "reference": "references/handoff-map.md",
        "target_skill": "the connection troubleshooting flow",
        "os_family": "any",
    },
    "handoff-security": {
        "label": "Attack-driven traffic drop, lockout policy, or ransomware damage",
        "gate": "handoff",
        "layer": "security axis",
        "reference": "references/handoff-map.md",
        "target_skill": "security handling, with this skill's data-rescue ordering",
        "os_family": "any",
    },
    "unknown": {
        "label": "Insufficient evidence to classify",
        "gate": "unknown",
        "layer": "undetermined",
        "reference": "references/evidence-checklist.md",
        "os_family": "any",
    },
}

# ---------------------------------------------------------------------------
# Screen-text patterns. Lower-cased substrings matched against the transcribed
# console or VNC text. `proves` / `not_proves` are printed verbatim so the
# report cannot overstate what the string supports.
# ---------------------------------------------------------------------------
ERROR_PATTERNS = (
    {
        "branch": "grub-loader",
        "patterns": ("grub rescue", "grub>", "error: unknown filesystem",
                     "unknown filesystem", "normal.mod", "entering rescue mode"),
        "proves": "the loader started and could not load its configuration or modules",
        "not_proves": "that the partition table or the data volume is damaged",
        "evidence": ["loader prompt `ls` output", "loader `set` output showing root and prefix",
                     "block device listing with filesystem types"],
    },
    {
        "branch": "grub-loader",
        "patterns": ("/boot/ not found", "no such device", "invalid boot device",
                     "missing operating system"),
        "proves": "no boot path resolved to a loadable system",
        "not_proves": "that the operating system files are present",
        "evidence": ["listing of the boot volume", "partition and filesystem table"],
    },
    {
        "branch": "efi-boot-entry",
        "patterns": ("boot manager", "tiano core", "welcome to grub", "bootx64.efi",
                     "boot##", "failed to open \\efi"),
        "proves": "firmware boot selection is looping between entries",
        "not_proves": "which entry is stale; both paths must be inspected",
        "evidence": ["photo or transcription of the firmware menu",
                     "listing of both EFI boot directories"],
    },
    {
        "branch": "fstab-mount",
        "patterns": ("emergency mode", "give root password for maintenance",
                     "press ctrl-d to continue", "failed to mount", "check /etc/fstab",
                     "a start job is running for", "timed out waiting for unit"),
        "proves": "the kernel started and the startup mount stage rejected an entry",
        "not_proves": "which entry; the two lines above the prompt name the failing unit",
        "evidence": ["verbatim contents of /etc/fstab", "blkid output", "findmnt output",
                     "the console lines preceding the prompt"],
    },
    {
        "branch": "filesystem-state",
        "patterns": ("errors=remount-ro", "read-only file system", "mounted read-only",
                     "run /init as init process", "cannot access inode",
                     "structure needs cleaning"),
        "proves": "the kernel protected a volume after recorded errors, or init hand-off stalled",
        "not_proves": "that the volume is unusable or the data is lost",
        "evidence": ["kernel ring buffer tail", "mount options in effect", "free space usage"],
    },
    {
        "branch": "post-update-normal",
        "patterns": ("configuring updates", "working on updates", "getting windows ready",
                     "just restarting", "retrying update", "do not turn off your computer",
                     "configuring windows updates"),
        "proves": "the system is completing an update transaction during startup",
        "not_proves": "that the transaction is stuck; progress and elapsed time decide that",
        "evidence": ["elapsed time since the attempt started", "whether any on-screen state changes"],
    },
    {
        "branch": "post-update-kernel",
        "patterns": ("kernel panic", "vfs: unable to mount root fs", "not booting: no init",
                     "general protection fault", "killed", "out of memory"),
        "proves": "the kernel loaded and failed while bringing up the root or an early component",
        "not_proves": "that the previous kernel would boot; test that entry explicitly",
        "evidence": ["running kernel reported by an older entry, if any boots",
                     "installed kernel and loader package versions"],
    },
    {
        "branch": "windows-bsod",
        "patterns": ("stop code", "termination code", "blue screen", "inaccessible_boot_device",
                     "reference_by_pointer", "automatic repair", "preparing automatic repair",
                     "your pc ran into a problem", "bugcheck"),
        "proves": "a Windows start-time crash occurred and, when printed, names a check code",
        "not_proves": "the responsible component; that needs the dump or the named module",
        "evidence": ["check code and all four parameters", "the named module if the screen shows one",
                     "whether kernel dumps are enabled and where they are written"],
    },
    {
        "branch": "windows-bsod",
        "patterns": ("bootmgr is missing", "winload.efi", "0xc000000f", "0xc0000225",
                     "winload has failed because the digital signature"),
        "proves": "the Windows boot files or boot configuration are unusable",
        "not_proves": "that the volume data is lost",
        "evidence": ["state of the system reserved volume", "whether the boot manager file exists"],
    },
    {
        "branch": "handoff-capacity",
        "patterns": ("no space left on device", "disk full", "insufficient disk space",
                     "errorcode 8010", "not enough space", "cannot fit", "inode"),
        "proves": "the failure is driven by free space or inode exhaustion",
        "not_proves": "that the boot path is damaged",
        "evidence": ["free space per volume", "largest paths on the system volume"],
    },
    {
        "branch": "handoff-expansion",
        "patterns": ("gpt", "mbr", "partition table", "lvm", "physical volume",
                     "volume group", "does not reflect the new size"),
        "proves": "the problem is in the partition or layout layer, typically after an expansion",
        "not_proves": "that data is lost; layout metadata can often be reconstructed by the owner",
        "evidence": ["reported versus visible size", "partition table type", "physical volume list"],
    },
    {
        "branch": "handoff-instance-state",
        "patterns": ("stuck in starting", "long time starting", "stopping for", "pending state",
                     "operating system starting", "stopped value never reached"),
        "proves": "the instance lifecycle state, not the guest boot path, is what is not advancing",
        "not_proves": "the underlying cause; this class is often closed without one",
        "evidence": ["status observed across an interval", "the change that preceded it"],
    },
    {
        "branch": "handoff-io",
        "patterns": ("iops", "throughput", "disk busy", "io saturated", "100% disk",
                     "await", "cpu 100"),
        "proves": "resource exhaustion can make a live system unreachable",
        "not_proves": "that a boot failure is present",
        "evidence": ["utilisation counters over the failure window", "the workload responsible"],
    },
    {
        "branch": "handoff-patch",
        "patterns": ("error code 133", "update failed", "patch install", "vulnerability fix",
                     "agent is running", "wsus", "windows update error"),
        "proves": "the failing thing is the installation action, not the boot path",
        "not_proves": "that the system is unbootable; confirm the boot state first",
        "evidence": ["the installer error code", "whether the OS reached logon"],
    },
    {
        "branch": "handoff-connection",
        "patterns": ("remote desktop", "rdp", "ssh", "workbench", "connection refused",
                     "timed out", "vnc works", "password is incorrect", "account is locked",
                     "0xd07"),
        "proves": "the OS is likely serving while a login channel is failing",
        "not_proves": "a boot failure; a working VNC screen actively disproves one",
        "evidence": ["what the console screen shows", "whether the service listens"],
    },
    {
        "branch": "handoff-security",
        "patterns": ("blackhole", "ddos", "all inbound traffic", "weax", ".locked",
                     "read decrypt", "ransomware", "encrypted all files", "webshell"),
        "proves": "an external attack or an encryption event is in play",
        "not_proves": "that the boot configuration is the primary fault",
        "evidence": ["whether unrelated services also became unreachable",
                     "file name extensions on system files"],
    },
)

# Cloud status strings that decide the step-0 gate.
BOOTABLE_STATUS_VALUES = ("Running",)
NON_BOOTABLE_HINT_STATUS = ("Stopped", "Stopping")

# ---------------------------------------------------------------------------
# In-guest evidence plan. Non-mutating commands only, presented for the
# CUSTOMER to run; this skill never dispatches them (see SKILL.md gate 2).
# ---------------------------------------------------------------------------
EVIDENCE_PLANS = {
    "grub-loader": {
        "linux": (
            {"cmd": "lsblk -o NAME,SIZE,FSTYPE,UUID,MOUNTPOINTS",
             "why": "shows which partition the loader should be pointed at", "kind": "query-only"},
            {"cmd": "blkid",
             "why": "reports the real filesystem identifiers for every volume", "kind": "query-only"},
            {"cmd": "ls -l /boot /boot/grub2 2>&1 | head -50",
             "why": "distinguishes a configuration problem from missing content", "kind": "query-only"},
        ),
        "windows": (),
    },
    "efi-boot-entry": {
        "linux": (
            {"cmd": "lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS",
             "why": "identifies the EFI system partition mount point", "kind": "query-only"},
            {"cmd": "ls -l /boot/efi/EFI 2>&1",
             "why": "shows which boot directories exist and whether a configuration file sits beside the loader",
             "kind": "query-only"},
        ),
        "windows": (),
    },
    "fstab-mount": {
        "linux": (
            {"cmd": "cat /etc/fstab", "why": "the recorded mount entries, verbatim", "kind": "query-only"},
            {"cmd": "blkid", "why": "the identifiers that actually exist now", "kind": "query-only"},
            {"cmd": "findmnt", "why": "what the running system managed to mount", "kind": "query-only"},
            {"cmd": "findmnt --verify", "why": "validates the file before the next reboot", "kind": "query-only"},
        ),
        "windows": (),
    },
    "filesystem-state": {
        "linux": (
            {"cmd": "dmesg | tail -n 100", "why": "shows the errors the kernel recorded for the volume",
             "kind": "query-only"},
            {"cmd": "findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS", "why": "shows the read-only state and its options",
             "kind": "query-only"},
            {"cmd": "df -h", "why": "free space, which decides whether capacity is the real axis",
             "kind": "query-only"},
        ),
        "windows": (),
    },
    "post-update-kernel": {
        "linux": (
            {"cmd": "uname -r", "why": "which kernel the system actually booted", "kind": "query-only"},
            {"cmd": "ls -l /boot", "why": "whether a previous kernel and its startup image remain",
             "kind": "query-only"},
            {"cmd": "df -h /boot", "why": "a full boot volume silently fails a loader rebuild", "kind": "query-only"},
        ),
        "windows": (),
    },
    "windows-bsod": {
        "linux": (),
        "windows": (
            {"cmd": "Get-Volume", "why": "free space on the system volume", "kind": "query-only"},
            {"cmd": "Get-WinEvent -LogName System -MaxEvents 100",
             "why": "the boot-time error records, including the bugcheck source", "kind": "query-only"},
            {"cmd": "driverquery", "why": "third-party drivers loaded at start time", "kind": "query-only"},
            {"cmd": "Get-ChildItem C:\\Windows\\Minidump", "why": "whether crash dumps exist to analyse",
             "kind": "query-only"},
        ),
    },
    "boot-files-lost": {
        "linux": (
            {"cmd": "ls -l / /boot /etc | head -60",
             "why": "an empty boot or configuration directory ends the repair ladder", "kind": "query-only"},
            {"cmd": "df -h", "why": "volume usage, as read from the mounted copy", "kind": "query-only"},
        ),
        "windows": (
            {"cmd": "Get-ChildItem C:\\ -Force | Select-Object -First 40",
             "why": "whether system directories are present or renamed", "kind": "query-only"},
        ),
    },
}

# ---------------------------------------------------------------------------
# Manual guidance: what the customer does to fix each in-scope branch. These are
# descriptions of human actions with their risk, never commands to execute.
# ---------------------------------------------------------------------------
MANUAL_GUIDANCE = {
    "grub-loader": (
        "Confirm a snapshot at 100 percent and an approved stop window.",
        "Start from a repair environment, or attach the disk to a healthy instance in the same zone.",
        "Verify the boot partition's real identifier before writing anything down.",
        "Reinstall the loader for the confirmed firmware mode, then regenerate its configuration and "
        "the startup image in the same pass.",
        "On a UEFI instance, refresh both the distribution-named entry and the fallback entry, so a "
        "boot-order change cannot strand the instance again.",
        "Reboot twice before declaring success; the second cycle is what exposes a stale fallback.",
    ),
    "efi-boot-entry": (
        "Establish the firmware mode and list the existing boot entries from a working environment.",
        "Compare the loader version in the fallback path with the one in the distribution path.",
        "Recreate the intended entry, then re-point the fallback path at the same loader version.",
        "Confirm the boot order survives a power cycle.",
    ),
    "fstab-mount": (
        "Comment out only the failing data-disk entry, and say so in the change record; that is a "
        "temporary unblock, not a fix.",
        "Never comment out a root, boot, or EFI entry to get past emergency mode.",
        "After the system starts, re-add the entry with a persistent identifier and the filesystem type "
        "that the device actually reports.",
        "Validate the edited file before the next reboot and report which of the two claims you hold.",
    ),
    "filesystem-state": (
        "Copy what matters out of the volume before any consistency repair; a repair rewrites metadata "
        "and can turn a readable volume into an unreadable one.",
        "Never run a consistency repair against a mounted volume.",
        "Perform it from a repair environment with the volume unmounted, on the customer's decision, "
        "after a completed snapshot.",
    ),
    "post-update-kernel": (
        "Boot an older loader entry first, if one exists, and record the kernel it reports.",
        "Regenerate the loader configuration and the startup image together, from a working environment.",
        "Decide deliberately whether automatic kernel upgrades stay enabled after recovery.",
    ),
    "post-update-normal": (
        "Wait within the customer's tolerance while the screen still changes.",
        "Before any forced power transition, confirm a completed snapshot and accept that stopping mid "
        "transaction may leave the volume needing a consistency pass.",
    ),
    "windows-bsod": (
        "Work the fixed ladder: safe mode and remove the most recent third-party component, then "
        "last-known-good configuration, then offline boot-file checks, then a configuration-unit restore.",
        "Stop and move to data rescue when every rung reproduces the same crash.",
        "Treat safe mode as a diagnostic channel only; services do not run there.",
    ),
    "boot-files-lost": (
        "Do not spend another repair cycle on configuration when the content is gone.",
        "Go to the rescue exits: roll back to an earlier usable snapshot, or copy the data out through a "
        "disk built from the newest snapshot.",
    ),
}
