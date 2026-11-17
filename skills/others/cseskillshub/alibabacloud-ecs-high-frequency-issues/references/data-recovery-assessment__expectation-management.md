# Expectation Management (fixed wording for hard conclusions)

Wording sourced from reviewed support conversations and official mechanics;
deliver it calmly and evidence-first. The conclusion is only as strong as
the customer-supplied evidence; emotion, compensation and account-side
requests still go to human channels.

## Core mechanism statements (reuse verbatim)

- **No invisible safety net.** Alibaba Cloud does not keep an automatic copy
  of customer data inside an ECS instance. Snapshots, images and backups
  exist only if the customer created or configured them beforehand.
  (Recurring customer assumption; reviewed tickets repeat the same answer.)
- **Release is permanent.** After an instance is released and the retention
  window has passed, disk data is permanently deleted. Paying a bill does
  not bring the old instance or its data back; the configuration can be
  reproduced by a new purchase, and a custom image -- if one exists --
  restores the system environment quickly.
- **Reinstall clears the system disk only.** Replacing the operating system
  (or re-initializing the system disk) wipes the system disk; attached data
  disks keep their content. Lost system-disk data without a prior snapshot
  cannot be restored by the platform.
- **Rollback restores data state, not running state.** A snapshot rollback
  brings back the file-data state of the snapshot moment; services that had
  no autostart must be started manually afterwards. (Reviewed conversation
  where a rolled-back site looked "still broken" for exactly this reason.)
- **Cache is not disk.** Data held only in a cache process (for example
  Redis without persistence) was never on disk; a restart that clears it is
  not a recoverable disk-data loss.
- **Cloud disk and local disk differ after expiry.** Cloud disks stay
  retrievable for a limited retention window after expiry (about fifteen
  days per the renewal notice), while local (instance-storage) disks are
  cleared once the instance enters the recycling phase.
- **Old backup is not the target moment.** If the only surviving snapshot
  predates what the customer needs, the honest verdict is partial: restore
  to the available point or extract from it; do not label it a full
  recovery.
- **No stamped attestation.** A sealed certificate stating that data cannot
  be recovered is not issued -- reviewed practice shows human support can
  only cite official documentation too. Direct the request to the human
  channel; this skill neither issues nor promises documents.
- **Third-party recovery is out of scope.** Ransomware decryption and deep
  file-system forensics are not a platform capability; specialized third-party
  services are the only route, and this skill only assesses which surviving
  backup can be used and how.

## Structure of a NOT-RECOVERABLE delivery

1. **Evidence recap first**: the read-only instance check result (not visible
   / released) plus the customer's own confirmed inventory (no snapshots,
   no images, no backups), each attributable.
2. **The mechanism sentence** from above that fits the carrier and event.
3. **What still can be done**: rebuild path (new purchase, any surviving
   partial asset, off-instance copies), and reconciliation of business
   records.
4. **Prevention list** (auto snapshot policy, database-consistent backups,
   off-instance copies, renewal reminders) so the conversation closes with
   forward value.
5. **Boundary declarations**: no compensation promises, no attestation,
   no third-party guarantees; emotion-driven escalations go to human
   support with this evidence summary attached.

## Phrases to avoid

- "Maybe someone at the provider can dig it out from their side" -- no
  such channel exists.
- "Try a recovery tool, it usually works" -- tools recover only if blocks
  were not overwritten; say that condition every time.
- Any promise softer than "we will conclude as soon as your console check
  comes back" while evidence is still missing.
- Blaming the customer ("you should have backed up"); state mechanics,
  not fault.
