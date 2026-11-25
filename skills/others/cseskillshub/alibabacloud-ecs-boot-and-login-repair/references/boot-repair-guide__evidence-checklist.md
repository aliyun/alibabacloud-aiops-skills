# Evidence checklist

The unit of work in this skill is an evidence set, not an opinion. This file fixes what a minimum
evidence set looks like per branch, in what format the customer should paste it, and what conclusion is
licensed by what was actually supplied. The collector is
`python3 scripts/axes/boot_repair_guide/boot_repair_guide.py evidence-plan --branch <branch-id>`, which prints one command at a
time with its purpose, its non-mutating nature, and its expected output shape.

Every item here is **run by the customer**, in the guest via VNC or SSH, or in a mounted repair
environment. This release does not dispatch commands into the instance. Where the customer declines to run
something, mark the affected conclusion as unsupported and report `STATUS: DEGRADED`.

## Global set (collect first, all branches)

| Item | Source | Format to paste |
|---|---|---|
| Region id and instance id | Customer | plain text |
| Instance status and last start attempt | `profile` subcommand | script output |
| Reported operating system name, version, image id, instance type, zone | `profile` subcommand | script output |
| The exact screen text, transcribed completely | Customer, from the console screen | verbatim, do not summarise |
| Console diagnostic verdict, if run | Customer | the full verdict paragraph, including which checks passed |
| Time of the failure and the change immediately before it (update, upgrade, resize, password reset, disk operation, application install) | Customer | one line, with a timezone |
| Snapshot state: exists, identifier, creation time, progress percentage, retention rule | Customer, from the console | one line per snapshot |
| Can the instance be stopped, and in what window | Customer | yes or no plus the window |
| Is any other instance in the same zone available to serve as a rescue host | `profile` on the candidate | script output |
| Working guest credential (logon user, and whether a key pair is bound) | Customer | yes or no only — never the credential itself |

## grub-loader and efi-boot-entry

| Item | Command the customer runs | What it decides |
|---|---|---|
| Loader-visible partitions and the recorded prefix | At the loader prompt: `ls` then `set` | Whether the boot volume is readable at all, and which partition the loader believes holds it |
| Block devices, partitions, filesystem types, identifiers | `lsblk` and `blkid` | Whether the loader's recorded prefix matches a real filesystem |
| Boot volume contents | `ls` of the boot directory and its loader subdirectory, plus the module directory the prefix names | Whether this is a configuration problem (repairable) or content loss (rescue) |
| EFI system partition layout | `ls` of the EFI directory, listing both the distribution-named path and the fallback path, plus whether a configuration file sits beside each loader binary | Whether the fallback path is stale, which is the usual reason a "fixed" boot loops again after a firmware change |
| Initial RAM disk and kernel presence | `ls` of the boot directory filtered to kernel and startup-image files | Whether the loader entry can resolve its own files |
| UEFI boot entries | `efibootmgr` output from the running or rescue system | Whether the intended entry exists and is first |

Licensed conclusion with all six: the loader layer is misconfigured, and the exact repair targets are named.
Licensed with the screen text only: the failure is in the boot loader layer, and the sub-case is unresolved.

## fstab-mount

| Item | Command the customer runs | What it decides |
|---|---|---|
| The file as it now stands | `cat /etc/fstab`, pasted verbatim with every field | The candidate line |
| Reality of the devices | `blkid` and `lsblk` | Whether each recorded identifier resolves |
| What is actually mounted | `findmnt` | Whether the failure is data-only or touches root, boot, or the EFI partition |
| Mount-table self-check | `findmnt --verify` | Whether an edit made before the reboot was correct |
| The two lines above the emergency prompt | Customer transcription | Which unit failed; this is where the failing device is named |
| Whether the disk exists on this instance at all | Console disk list for the instance | Image-vs-instance restore semantics: an entry inherited from an image with no matching volume |

Feed the first two paste outputs to `fstab-compare` for a per-line verdict. Licensed conclusion: which line
fails and why. Editing the line is the customer's action, and the guidance must state that a commented-out
data disk is a temporary unblock.

## filesystem-state

| Item | Command the customer runs | What it decides |
|---|---|---|
| Kernel messages about the volume | `dmesg` tail, pasted | Whether errors were recorded and whether the volume was remounted read-only as protection |
| Mount options in effect | `findmnt` output for the root volume | Whether an error-action option forced the read-only state |
| Free space and inode usage | `df -h` and `df -i` | Whether capacity is the actual axis; route out if so |

An integrity check is never part of this skill's output as a command to run against a mounted volume. It is
a manual step performed offline from a repair environment, on an unmounted volume, after a completed
snapshot, by the customer, who accepts that consistency repair rewrites metadata. The evidence this skill
does supply is the ordering: copy what matters out before repairing, because repair can turn a readable
volume into an unreadable one.

## post-update-kernel and post-update-normal

| Item | Command the customer runs | What it decides |
|---|---|---|
| Running kernel | `uname -r` | Whether an older entry still boots, which splits "new kernel broken" from "boot path broken" |
| Installed kernel and loader packages | The distribution package query for the loader and kernel packages | Version skew between loader, configuration, and kernel |
| Whether the update completed | Distribution transaction log or the update history screen | Whether the interruption happened mid-transaction |
| Boot entries present | The loader menu contents, or its configuration file | Whether a known-good entry is selectable |
| Free space on the boot volume | `df -h` for the boot and root mount points | Whether the kernel or startup-image regeneration could have failed for lack of space |

## windows-bsod

| Item | Source | What it decides |
|---|---|---|
| The four-tuple: code, parameters, module, dump path | Customer screen transcription | The triage class |
| Whether kernel dumps are enabled | Customer, from system properties | Whether the next crash will be diagnosable |
| Dump file presence and path | Customer, in the system root | Whether analysis is even possible |
| Recently installed third-party components, especially protection, backup, encryption, and compatibility products | Customer statement, or `driverquery` output pasted back | The dominant suspect class |
| Free space on the system volume | `Get-Volume` or `Get-PSDrive` | The capacity-plus-update combination |
| Update failure history | Event viewer, pasted | Whether the update story is supported by evidence |
| Configured memory against the OS release minimum | `profile` output plus the published requirement | The false-blue-screen class |
| End-of-support status of the reported OS | `profile` output | Whether a patch for the suspected problem can exist |

Dump analysis is out of scope and out of capability here. Nothing in this evidence set licenses naming a
specific driver unless the screen text named it.

## boot-files-lost (the "is it even repairable" set)

| Item | Command the customer runs | What it decides |
|---|---|---|
| Contents of the boot directory and of the configuration directory | `ls -l` of each, pasted | Whether content loss occurred; an empty boot or configuration directory ends the repair ladder |
| Whether the volume mounts read-write in a repair environment | `findmnt` after mounting | Whether the data is still salvageable |
| Snapshot inventory and the oldest usable point | Customer | Which exit is available |

This is the evidence set that the best self-service customers produce on their own before opening a request.
Asking for it explicitly is usually faster than three rounds of guesswork.

## Reporting discipline

For every conclusion, name the artifact behind it and the call that produced it, with the run's session id
and timestamp. Where a channel was unavailable, say which and what it cost the analysis:

```
Evidence gaps: no offline inspection of the EFI system partition, therefore the fallback boot path
could not be confirmed stale. Branch grub-loader is supported at category level only.
STATUS: DEGRADED
NEXT_ACTION: Customer mounts the volume from the console repair entry and pastes `ls` of both EFI paths.
```
