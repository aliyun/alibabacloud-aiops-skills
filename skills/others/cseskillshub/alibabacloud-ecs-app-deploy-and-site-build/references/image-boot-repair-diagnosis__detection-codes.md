# Image-detection items: meaning, verified readings, manual steps

Scope discipline: every statement below is either (a) a literal detection
item or console wording seen in real support tickets for this tier, (b) a
rule quoted from an official help page cited at the end, or (c) an explicit
"not settled by the docs" admission. Where the docs do not settle an impact
question, say so — never upgrade a WARN to a blocker or downgrade a
critical to "ignorable" without the reading that proves it.

## The two grades customers confuse most

- **WARN** (e.g. an agent reported as not installed): an advisory about
  image *contents*. It does not stop the image from being used; the
  uncertainty customers hit is whether a given WARN must be fixed for a
  given OS-level feature — that question is **not settled uniformly by the
  docs in this batch**; the honest answer is "import is not blocked; the
  feature needs the component, and installing it is a customer-run step on
  a booted instance."
- **Critical** (e.g. the mount-target item below): the detection grade of
  the item, NOT a verdict that the image or backup is unusable. Customers
  preparing a system reinstall treat a critical grade as "my snapshot is
  broken" — the grade describes one configuration defect, and the
  fix-then-rebuild loop in `repair-failure-codes.md` settles whether it
  mattered. Detection results have **no verified read-only pull API**: the
  customer pastes the report; this skill interprets it.

## Disk.MountTargetDirNotFound (reported as critical)

**Literal meaning.** A mount target directory declared in the image's
fstab does not exist inside the image.

**Why it appears everywhere.** Observed on *every* custom image of one
customer account across regions: instances carry only a system disk, while
the fstab (often template-era or from a since-removed data disk) declares
mounts whose targets were never created. A repeated occurrence across
images built from the same source is a template defect, not per-image
noise.

**What only a guest reading can settle.** Whether the boot itself is at
risk depends on the options of the specific fstab line (a stale line can
be boot-blocking or wholly ignorable depending on mount flags and whether
the source device still exists). No cloud API sees the fstab contents:
1. ask the customer to paste the fstab file (this skill never reads file
   contents itself — `cat`/`grep` are outside the whitelist);
2. with the instance Running (source instance or a throwaway instance
   built from the image), diff live mounts against the declared targets
   with the whitelisted reads: `findmnt`, then `stat` / `ls` on each
   declared target directory;
3. target directory missing → the detection finding is confirmed with a
   concrete path; target exists and mounts cleanly → the item is
   informational for this image.

**Manual resolution (customer-run).** Comment out or correct the stale
fstab line for the device that no longer exists (or create the missing
target directory if the mount is wanted), boot-test the change on a
throwaway instance, then rebuild the custom image and re-run detection.
Image rebuild and detection re-trigger are console actions by the
customer; this skill's role after that is the read-only recheck
(`verify-repair` mode + the new pasted report).

## CloudAssistant / SecurityCenterAgent (Aegis) not installed (WARN)

Both come from image-detection reports (including the offline check script
run against a locally prepared image, e.g. a minimal RHEL export). Official
and marketplace images integrate the agents; locally built images usually
do not, which is exactly what the WARN means.

- Neither missing agent blocks boot. Cloud Assistant absence breaks the
  *guest channel* (remote commands, Workbench password-free login), not
  the OS. Security Center absence is a security-coverage gap, not a boot
  or import condition.
- "Is it mandatory?" — the import itself is not blocked (WARN grade).
  Whether a given feature needs it is a feature-side question; answer with
  the doc pointer below and, when unsure, say the doc does not settle it.
- Verification without guessing: the install directories **must come from
  the official install docs, never from memory** — no directory path for
  either agent is hardcoded anywhere in this skill. With the instance
  Running, `stat`/`ls` against the *documented* path confirms presence.
- Resolution: installing or debugging either agent is a WRITE operation
  outside this tier — the customer installs per the official doc and
  rebuilds the image; agent runtime faults hand off to
  `alibabacloud-ecs-cloud-assistant-diagnosis` (Cloud Assistant axis) or
  the security product's own channel (Aegis axis).

## NVMe driver adaptation (image compatibility)

Symptom wording: "imported image cannot be selected when purchasing an
8i-family instance" or a guest that dies before mount on an NVMe-only
family. Newer instance families attach the system disk as NVMe; an image
whose kernel/initramfs lacks the driver cannot boot there.

- Read-only check available: `DescribeImages` returns a per-image
  `Features.NvmeSupport` value on records that carry it (response shape
  verified live 2026-09-16). When the field is absent or unreadable for a
  custom record, fall back to the purchase-time error statement; never
  assert support without the field or the error.
- Fix is image rebuild with an NVMe-capable kernel/initramfs (customer,
  off-image); driver injection is out of scope.

## Invalid image format in header (import failure)

A literal upload-import error: the raw image file's header does not satisfy
the import format requirements (classic cause: a split-descriptor VMDK from
desktop hypervisors). Import never lands, so nothing guest-side applies —
resolution is local conversion with the customer's own tool to a format the
import doc accepts, then re-upload. Conversion runs on the customer's
machine; this skill maps the error to the doc and stops there.

## Detection tool and console entry points

- Offline/standalone check of an image against import requirements and its
  detection-item wording:
  <https://help.aliyun.com/zh/ecs/user-guide/check-whether-an-image-meets-the-import-requirements.md>
- Console image detection and repair mechanism (where the critical grades
  and repair tasks come from):
  <https://help.aliyun.com/zh/ecs/user-guide/detect-custom-images-and-repair.md>
- Import format requirements (header errors, supported formats):
  <https://help.aliyun.com/zh/ecs/user-guide/import-a-custom-image.md>

No other URLs are cited for this axis: the NVMe adaptation and fstab fix
pages had no verified hit in this batch's evidence, so they are described
in words only.
