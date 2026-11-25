# Boot error catalog

Each entry is a string a customer can actually see on the VNC screen, in the console diagnosis verdict, or
in a crash report, plus what it proves, what it does **not** prove, and the next step. Matching is
implemented in `_constants.ERROR_PATTERNS` and driven by
`python3 scripts/axes/boot_repair_guide/boot_repair_guide.py classify --text "..."`.

Two disciplines apply to every row:

- **Report what is proven, not what is suspected.** The right-hand column "Does not prove" exists because
  the most expensive mistakes in this tier came from reading a boot-time message as a data-loss verdict.
- **Ask for the complete string.** Truncating a message loses the device name, the module name, and the
  code, which are exactly the parts that decide the branch. Ask the customer to transcribe the whole screen
  or the whole diagnosis paragraph, including identifiers.

## Linux: boot loader and firmware stage

| Exact string | Proves | Does not prove | Branch and next step |
|---|---|---|---|
| `grub>` | The loader started but found no usable configuration | The data volume is damaged | `grub-loader`: establish from the prompt which partition the loader sees (`ls` at the prompt) and what `prefix` and `root` are set to; then rebuild configuration from a repair environment |
| `grub rescue>` | The loader lost its module directory | The partition table is destroyed | `grub-loader`: set `root` and `prefix` at the rescue prompt to confirm the boot partition is readable, then reinstall the loader modules and configuration manually |
| `error: unknown filesystem` | The loader has no driver for the filesystem it was pointed at, or the partition no longer holds that filesystem | That the partition table is gone or the content is lost | `grub-loader`: enumerate partitions and identify each one's filesystem type from a repair environment; a mismatch between the recorded prefix and the real filesystem is the usual finding |
| `file '/boot/grub2/i386-pc/normal.mod' not found` | The module directory referenced by `prefix` does not exist at that path | That the root filesystem is healthy | `grub-loader`: check whether `/boot` still has content; if it is empty this is `boot-files-lost` and repair is off the table |
| `Entering rescue mode...` (from the loader) | The loader deliberately dropped to rescue | — | `grub-loader`: collect `ls`, `set`, and the block-device listing before changing anything |
| `Boot Manager` to `debian` to `Welcome to Grub` back to firmware, repeating | The selected UEFI entry starts a loader that fails and hands control back | That the disk is unreadable | `efi-boot-entry`: identify both the NVRAM entry and the removable-media fallback path, and check whether each one's configuration file exists; both paths must end at the same loader version |
| `\EFI\BOOT\BOOTX64.EFI` present, no `grub.cfg` beside it | The fallback path holds an old loader with no configuration | — | `efi-boot-entry`: after repairing the primary entry, refresh the fallback copy too, otherwise the next firmware reset reproduces the loop |
| `Missing operating system` / `no bootable device` | No boot path was selected at all | That the OS files exist | `efi-boot-entry` or `boot-files-lost`: first confirm the boot partition is still partitioned and formatted |

## Linux: kernel and init stage

| Exact string | Proves | Does not prove | Branch and next step |
|---|---|---|---|
| `Run /init as init process` and then nothing | Execution reached the initial RAM disk and the hand-off did not complete | That the hardware is faulty | `filesystem-state` or `post-update-kernel`: check whether the root volume is being rejected, and whether the initial RAM disk matches the kernel that is loading |
| `Give root password for maintenance` , `Press Ctrl-D to continue` | The system dropped to emergency mode on purpose | The cause: it is a mount, filesystem, or unit failure reported just above | `fstab-mount`: read the two lines before the prompt, they name the failing mount unit |
| `A start job is running for ...` repeating with a growing counter | A boot unit is waiting on a device that never appears | A hang requiring a reboot | `fstab-mount`: identify the waited-on device and compare it with what actually exists |
| `mounted filesystem read-only` , `errors=remount-ro` in the mount options or kernel messages | The kernel protected a volume after recorded errors | That the volume is unusable or the data is lost | `filesystem-state`: data is normally still present; copy it out before any consistency repair, and never run a consistency repair on a mounted volume |
| The device named in the message does not exist, e.g. `/dev/vdb1` while the disk is actually `/dev/nvme0n1p1` | The repair instruction and the real device naming disagree | That either name is wrong in general | Resolve real device names before running anything; a repair command aimed at the wrong device can damage a healthy volume |
| `status=205/LIMITS` when starting the secure shell daemon from a rescue environment | The rescue environment's resource limits or encryption policy block the unit | A problem in the customer's own system | Set the rescue environment's policy variable aside, or start the daemon directly with an explicit configuration file and port |
| `Too many connections` from a database | The service is overloaded or a volume filled up | A boot failure | Not this skill: capacity or performance axis, route out |

## Linux: mount configuration

| Exact string | Proves | Does not prove | Branch and next step |
|---|---|---|---|
| `Check /etc/fstab.` , `Failed to mount ...` naming a data disk | One mount entry cannot be satisfied | That the entry must be deleted forever | `fstab-mount`: comment out only the failing data-disk line, reboot, verify, then re-add it correctly with a persistent identifier |
| The reported mount point's device does not exist, or the filesystem check of a volume reported errors during startup (the console diagnosis wording covered by the fstab error article) | Either the device identifier is stale or the volume has inconsistencies | Which of the two it is | `fstab-mount` first, since it is the cheaper branch; compare recorded identifiers against the actual devices before touching consistency tools |
| Image detection reports a severe mount configuration risk on an image that boots correctly | The scanner evaluated the image offline and could not see the mount target directory | A real boot defect | False positive: leave the file alone. Editing a working file is how a healthy instance becomes an emergency-mode instance |
| A `swap` entry reported as invalid on an image | Same offline limitation | — | False positive, unless the swap device genuinely disappears on the new instance |

## Windows

| Exact string | Proves | Does not prove | Branch and next step |
|---|---|---|---|
| Blue screen with `Stop Code:` or `Termination code`, bugcheck check code such as `0x18 (REFERENCE_BY_POINTER)` | A kernel-mode component faulted with a specific bugcheck and parameter set | Which component, until the dump is read | `windows-bsod`: collect the four-tuple (code, parameters, suspected module, dump path); see `references/boot-repair-guide__windows-bsod-triage.md` |
| `INACCESSIBLE_BOOT_DEVICE` | The boot volume's storage stack could not be initialised | That the disk itself failed | `windows-bsod`: suspect a storage or filter driver introduced by the last change, or an image and instance-type combination the guest cannot drive |
| `Automatic Repair couldn't repair your PC` , `Preparing Automatic Repair` looping | The boot or system files are unusable and the automatic pass failed | That the volume is gone | `boot-files-lost` or `windows-bsod`: check the system-reserved volume and boot configuration from offline media |
| `bootmgr is missing` , a boot file carrying an unexpected extension appended by an encryption tool | The boot manager file was deleted, renamed, or encrypted | That the whole volume is encrypted | Route to security handling first; this skill only sequences the snapshot, copy, and rebuild steps |
| A stop code naming a third-party driver module, e.g. a filter driver with `.sys` in the faulting stack | One vendor component is implicated | Root cause without the dump | Manual: remove or disable that component in safe mode, or offline; ask the vendor for a version validated on this release |
| `0xF7` with a GS security cookie overwrite reported by a kernel dump in an early-start driver | A third-party early-start driver corrupted its own stack | Which driver, when the module list is corrupted | Offline analysis with the vendor; if the customer cannot wait, the practical exits are safe mode, removing recent third-party software, or rebuild |
| A remote-login failure request identifier such as `019FD0AC-...` while VNC works | The remote desktop service path is failing | A boot failure | Not this skill: the OS booted; route to the connection path |
| `0xd07`-style account lockout reported while logging in | Lockout policy triggered, often by a stored credential replaying | A boot failure | Not this skill: security and policy axis |

## Codes that mean "not this skill"

`ErrorCode 8010` and error-code-133-class patch installation failures, a process holding a file the updater
needs, a volume with under a gigabyte free, an instance parked in `Starting`, saturated disk throughput,
blackhole routing after an attack. Each of these has appeared in tickets titled "server will not boot";
none of them is a boot failure, and naming them early is what saves the customer a repair attempt they do
not need.

## Strings that need a source before use

The following are expected in this tier but were not present in the reviewed evidence, so they are listed
as placeholders and must not be asserted to a customer until a documentation source is attached:
the `0xc000000f` and `0xc0000225` boot-configuration error codes, the exact localized automatic-repair
sentence, the `A start job is running for dev-...device` unit-name form, and every vendor-specific
filter-driver module name. Recognizing one of these strings when the customer supplies it is still correct,
because that is reading their evidence; what is not permitted is presenting the string back as an
established cause. `classify` reports a screen text it cannot match at all as the `unknown` branch rather
than mapping it to the nearest one.
