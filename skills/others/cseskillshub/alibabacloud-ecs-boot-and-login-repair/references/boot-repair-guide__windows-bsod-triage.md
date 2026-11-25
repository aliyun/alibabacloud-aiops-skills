# Windows start-time crash triage

Blue screens, automatic-repair loops, and crash-just-before-logon. This file defines what the skill can
conclude from a screen transcription, what it must not conclude, and the manual ladder.

**No capability in this skill reads a crash dump.** Dump analysis is a human, tool-mediated activity, and in
the reviewed evidence it required exporting the customer's volume to another account to obtain the log. Where
a dump is the only way to a specific cause, the correct output is: collect the four-tuple below, and either
open an offline support request or perform the analysis yourself; this skill will not name a driver.

## The four-tuple to collect first

Ask for all four in one request; partial reports stall:

1. The **bugcheck code** and its symbolic name (for example `0x18` `REFERENCE_BY_POINTER`, or
   `INACCESSIBLE_BOOT_DEVICE`).
2. The **four parameters** as printed.
3. The **suspected module**, if the screen names one (a `.sys` file name is the single most valuable line).
4. The **dump path**, and whether kernel or small dumps are enabled at all. On many instances the default
   page-file-backed setting writes nothing, so a crash with no dump is common and is itself a finding.

With 1 through 3 you can classify. Without them, the report says `unknown` and lists what to
capture on the next occurrence, including enabling kernel dumps so the next crash is diagnosable.

## Triage classes

| Class | Typical signal | Manual next step | Certainty the skill may claim |
|---|---|---|---|
| Third-party filter or security product loaded at start time | A named vendor `.sys` module; the failure began after installing a protection, backup, encryption, container, or compatibility product; safe mode reachable | Remove or disable the product from safe mode, or offline; ask the vendor for a release validated on this OS version; the reference case class was a filesystem filter driver mismanaging object references on a volume | Category, not the specific component, unless the screen names the module |
| Storage stack cannot reach the boot volume | `INACCESSIBLE_BOOT_DEVICE` | Check whether the instance type changed, whether a storage or controller driver was updated, and whether the volume is still attached and partitioned | Category |
| Boot or system files unusable | Automatic repair failure loop, missing boot manager | Boot-configuration repair from offline media, performed by the customer; if the boot manager carries an unexpected file extension, treat as a security incident | Category |
| Registry or critical system file damaged | Several distinct repair attempts all end at the same crash; last-known-good and a registry backup restore both fail | Stop the repair ladder and go to data rescue; expect this class to end in a rebuild | "Not repairable by configuration" is a legitimate conclusion here, backed by the failed ladder |
| Out-of-support image | The OS is an end-of-support release; a published vulnerability or a missing patch explains the crash and no update exists for it | Upgrade or replace the operating system after backing up; this is an intentional change with a downtime window and is customer-executed | The end-of-support fact is machine-checkable from the reported OS name; the causal link to the crash is not |
| Old image on a new instance type | A crash that disappears when the same image runs on an older instance type | Validate by creating a test instance from the same image on a conservative type; if it boots, the pairing is the problem | Category, and this one is cheap to test |
| Not a crash | Frozen screen from memory exhaustion, or a black screen at the logon stage | Check the configured memory against the OS release's published minimum and the current utilisation; this belongs to the capacity and performance axes | Route out; state that the evidence points away from a start-time crash |

The two highest-value habits from real cases: check whether a third-party protection product is installed
before theorising about the platform, and check whether the image and instance type pairing changed before
concluding that a driver is at fault.

## Safe mode is a diagnostic channel, not a recovery

Safe mode that loads successfully is strong evidence that the fault belongs to a third-party component
loaded in the normal start path. It does **not** mean the workload can run: services and drivers are not
loaded, so the business application and often the network-facing components stay down. Say this explicitly
when a customer proposes to "stay in safe mode until the weekend".

If safe mode rejects the credential, the offline password reset flow applies; a locally triggered reset from
inside the rescue path is a change to the customer's authentication state and requires their confirmation.

## The repair ladder, fixed order, one recorded attempt each

1. Boot into safe mode and remove or disable the most recently installed third-party component.
2. Last-known-good configuration.
3. Disable automatic restart so the screen text is captured, then re-attempt a normal start to collect the
   bugcheck.
4. Offline: verify the boot configuration and the system files from a repair environment.
5. Restore a registry backup, understanding that the backup may be old and that a stale hive can produce a
   system that boots with the wrong configuration.
6. Stop. Move to `references/boot-repair-guide__data-rescue-and-reinstall.md`.

Restarting the instance repeatedly is not a ladder rung. It is sometimes the fastest way to get a customer
working again, and when they choose it, state the three conditions: a completed snapshot exists, the business
has accepted the window, and a restart does not fix a driver or a corrupted file, so a crash collection step
(dump enabled, screen photographed) must be paired with it or the next occurrence teaches nothing.

## What the cloud API can and cannot tell you here

Available: the reported OS name and version, so end-of-support status is machine-decidable; the image
identifier; the instance type and its memory size, so "below the published minimum" is decidable; the
instance status; and monitoring counters if a separate performance skill is used. Never available: the
crash dump, the driver list, the update-failure history, the registry state. Say which of the two lists a
conclusion rests on.
