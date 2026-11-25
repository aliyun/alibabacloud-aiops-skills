# Boundary and handoff matrix

Most cases that land in this tier are not actually about disk encryption. The skill's job on
those is: name the symptom correctly, keep only the encryption-relevant read, and route. The
target skill names below are **provisional** - the injected evidence did not include the
batch's neighbour list, so align these with the final tier list before publishing.

## 1. Handoff table

| Symptom as the customer says it | Owner (provisional name) | What this skill still does | Evidence behind the row |
|---|---|---|---|
| "my data is encrypted by ransomware", "restore me from a snapshot", "my snapshots disappeared" | Snapshot and ransomware-recovery tier | Read whether the disks and snapshots exist and what their encryption fields say; no recovery attempt | A majority of this tier's ticket set is ransomware and snapshot-recovery wording, not disk-encryption questions |
| "the disk is full", "I grew the disk but the OS still shows the old size" | Disk capacity and partition tier | Nothing encryption-related, unless the customer also asks whether the disk is encrypted | Guest partition work needs in-instance commands |
| "SSH will not come up", "my key pair no longer works", "the VNC screen asks for a password" | Remote access and credentials tier | Nothing; note that "key" here is a login credential | Several cases in this tier were key-pair and login problems, misrouted by the word "key" |
| "Windows demands a 48-digit recovery key after a restart" | Guest OS volume encryption (Microsoft-side) | A single disambiguation sentence plus a snapshot-existence read if the customer wants a safety copy | BitLocker is not Alibaba Cloud disk encryption; no cloud read can retrieve that key |
| "change the operating system", "use this community image", "swap the system disk" | Image and operating-system tier | The encryption facts of the source disk and of any image chain, and the risk block | An operating-system swap re-initialises the system disk; the encryption option is only available as it is provisioned |
| "how much do snapshots cost", "they were removed while I was overdue", "issue a coupon" | Cost and billing tier | Nothing; the reads cannot see a bill | Snapshot removal after 15 days overdue was a real conversation in this tier's evidence |
| Instance id is not `i-` / `d-` / `s-` shaped, or the product is a simple application server | The owning product line | A clear statement that these ECS reads cannot see that product, and no encryption conclusion | A compliance question about a simple application server's system disk could not be answered from the ECS side at all |
| "give me a written attestation for an audit" | The customer's compliance or account path | The document checklist and the process; nothing is submitted on their behalf | Written-proof requests appear in this tier's evidence alongside the technical questions |

## 2. Canned handoff wording

**Ransomware or encrypted-data recovery**
*"Alibaba Cloud cannot undo strong ransomware encryption on your files, and that is not a
disk-encryption setting. Please halt all writes to the instance immediately and take a snapshot of
the current state first, then look for an older snapshot to recover from. Do not pay the
ransom, and consider reporting it to the police. Hardening guidance:
`https://help.aliyun.com/zh/security-center/use-cases/comprehensive-protection-plan-against-ransomware-attacks`.
This case belongs to the snapshot and ransomware-protection tier."*

**In-instance diagnosis or repair**
*"This skill does not run commands inside your instance. Mounting a rescue disk, editing
fstab or sshd, growing a partition or repairing a filesystem is done through the Cloud
Assistant / remote-connection path or by an engineer you authorise - and before any
authorisation, take a snapshot of every disk and wait for it to be usable."*

**Billing, invoices, overdue state**
*"Snapshots are post-paid; an overdue account has them automatically removed after 15 days and
there is no removal record to recover them from. I cannot read your balance or your order
history, so this belongs to the cost and billing tier. What I can give you is the disk and
snapshot inventory as read from the cloud side."*

**Windows-side recovery key**
*"That prompt is Windows volume encryption, managed by Microsoft and tied to the Microsoft
account that enabled it - not to an Alibaba Cloud KMS key. Retrieve the 48-digit recovery key
from that Microsoft account, and take a snapshot before any further change. Note that the
login password is not the recovery key; they are different things."*

**Another product line**
*"The id you gave me is not an ECS resource, so the ECS-side reads in this skill cannot see its
disk encryption. I will not infer an answer from the ECS rules; this belongs to that product's
own tier."*

## 3. What must never be claimed

- That data was recovered, a filesystem was repaired, a partition was grown, a service was
  restarted, or a configuration inside the guest was changed. None of it is in scope.
- That an order was placed, an invoice was checked, a written attestation was issued, or a
  ticket was submitted for the customer.
- That an unencrypted existing disk can now be encrypted in place.
- That a key type was determined, when the read only proved "encrypted".
- That a BitLocker or ransomware question is answered by an ECS disk-encryption read.
