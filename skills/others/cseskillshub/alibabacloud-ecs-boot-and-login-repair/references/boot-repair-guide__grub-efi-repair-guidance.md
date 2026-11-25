# Boot loader and EFI boot entry guidance

Scope: the machine powers on, firmware runs, and control never reaches a login prompt. The output stops at
a loader prompt, loops between firmware and the loader, or reports that a loader file is missing.

**Everything in this file is performed by the customer.** Reinstalling a boot loader, writing UEFI boot
entries, rebuilding an initial RAM disk, and repairing a Windows boot configuration all rewrite the thing
that lets the machine start. A wrong step here turns a repairable instance into a data-rescue case, so the
skill's role is to establish the mode, the evidence, and the order of operations, and to insist on the
snapshot gate first.

## Step A — establish the firmware mode before anything else

The repair differs completely between the two modes, and picking the wrong one produces a loader that
installs cleanly and still does not boot.

| Signal | Mode |
|---|---|
| A `grub rescue>` prompt naming `(hd0,msdos1)` style partitions | BIOS or legacy compatibility |
| A partition naming style like `gpt1`, `gpt2` from the loader prompt | GUID partition table, mode still to be confirmed |
| The firmware Boot Manager menu, an entry named after the distribution, or a TianoCore-based firmware screen | UEFI |
| An EFI system partition present, formatted FAT, mounted at `/boot/efi` | UEFI |
| A small BIOS-boot-signature partition of roughly one to two megabytes | BIOS mode on a GUID table |

Confirm with the partition and filesystem listing (`lsblk`, `blkid`) from a working environment. Record both
the partition table type and whether an EFI system partition exists; a GUID table can be booted in either
mode, which is why the mode question cannot be answered from the partition listing alone.

## Step B — map the boot path that actually exists

Two independent paths can hold a loader, and an upgrade commonly refreshes one and not the other:

1. **The NVRAM boot entry** — the entry the firmware selects, pointing at a file such as
   `\EFI\<distribution>\bootx64.efi` with a descriptive boot loader id.
2. **The removable-media fallback path** — `\EFI\BOOT\BOOTX64.EFI`, used when no NVRAM entry matches.

The failure mode that generates most of the tickets in this branch: the fallback path still contains an old
loader copy from before an upgrade, and the configuration file that loader reads is not beside it, so the
firmware selects the fallback, the loader finds no configuration, and the customer is staring at a `grub>`
prompt with a perfectly healthy root filesystem. The repair therefore has to leave **both** paths pointing at
the same loader version with a configuration file present; fixing only the NVRAM entry reproduces the loop
after any firmware reset or boot-order change.

Collect, from a repair environment with the customer's disk mounted:

- the loader directories present on the EFI system partition, and the version of each loader binary;
- whether a configuration file exists next to each binary, and its device and root stanzas;
- the loader module directory the recorded prefix points at, and whether it exists;
- the boot partition contents, in particular whether `/boot` still holds a kernel, an initial RAM disk, and a
  loader module directory;
- the block-device listing with identifiers and filesystem types, to compare against the recorded prefix.

If `/boot` or `/etc` is empty rather than merely misconfigured, stop: that is content loss
(`references/boot-repair-guide__boot-error-catalog.md`, `boot-files-lost`) and the correct next step is
`references/boot-repair-guide__data-rescue-and-reinstall.md`, not another loader reinstall.

## Step C — the manual repair ladder, in order

Record each attempt, what it was, and what changed. Attempting the same step four times without a log is the
pattern that produces an exhausted, unsupported instance and no information.

1. **Set the loader prefix and root at the prompt** to prove which partition the loader can read. This is
   non-destructive and tells you whether the boot volume is visible at all.
2. **Regenerate the loader configuration** from a repair environment with the customer's root mounted, after
   verifying that the identifiers it writes match the devices that exist.
3. **Reinstall the loader packages** for the correct mode and architecture, including the signed shim
   variants on a UEFI instance, then rebuild the initial RAM disk so the loader, kernel, and user-space
   startup contents belong to the same release.
4. **Reinstall the loader to the device** for the BIOS case, or write both the distribution-named entry and
   the removable-media fallback for the UEFI case, so that a boot-order change cannot strand the instance.
5. **Correct the firmware boot order** so the intended entry is first, and confirm the entry survives a
   power cycle.

A repair environment can be reached two ways, and the customer's situation decides which: the console
diagnosis and repair-disk entry described in `references/boot-repair-guide__offline-repair-channel.md`, or detaching the system
disk and attaching it to a healthy instance in the same zone as a data disk and entering the mounted system
with a change-root. Both require the instance stopped and the snapshot complete.

## Step D — verification that the repair worked

Do not declare the branch fixed on the strength of a successful command exit code. The evidence that closes
this branch is:

- the instance started, and the console screen shows the distribution booting past the loader;
- after logging in, the running kernel is the one the loader entry names;
- the loader configuration on disk names the devices that `blkid` reports;
- a second reboot reproduces the same successful start, since a boot-order or fallback problem only shows on
  the second cycle;
- for UEFI, the firmware still lists the intended entry after the reboot.

## Windows equivalent

The same shape of reasoning applies with different objects: the system reserved volume and its boot
configuration data store, the boot manager file, the boot configuration store, and the code integrity and
driver signature policies. The repair verbs (`bootrec`, `bcdboot`, rebuilding the boot configuration data
store, replacing the boot manager) are all destructive-capable and stay with the customer. Where a boot
manager file was deleted or renamed by an encryption tool, treat it as a security incident first: a
temporarily regenerated boot manager can bring the system up enough to copy data out, and is not a recovery
of the workload.

## Where this skill's knowledge stops

The cloud API cannot see the EFI partition contents, the loader version, the configuration file, or the
firmware boot entries. Everything above depends on a customer-supplied screen transcription, a pasted
read-only output, or an offline inspection performed by a human. State which of the three a conclusion rests
on, and when none is available, report the `unknown` branch rather than naming the most common cause.
