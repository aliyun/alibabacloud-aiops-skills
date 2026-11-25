# Handoff boundaries

A credential symptom is often the visible end of a cause that lives in another
tier. This page is the identify-and-hand-off table: recognise the trigger, say
the boundary in one sentence, name the target, and stop diagnosing here.

Source of truth: `HANDOFF_TABLE` in `scripts/axes/keypair_login_config/_constants.py`. The entry script
prints the matching row under `HANDOFF` in its report, and `handoff_for()` falls
back to "human support" when nothing matches, so a row is never invented.

Target skill names follow the batch skill list. Where a name has moved, the
boundary statement is what identifies the handoff, not the string.

## The table

| Trigger the customer shows | One-sentence boundary | Hand off to |
|---|---|---|
| Disk full, inode exhaustion, a resize that never shows inside the guest | A capacity problem, not a credential problem | `alibabacloud-ecs-disk-capacity-cleanup` |
| Disk IO or IOPS saturated, the system wedged, several symptoms at once | The logon failure is the visible end of an IO hang | `alibabacloud-ecs-disk-io-diagnosis` |
| The instance will not boot, or is stuck between states | An instance lifecycle problem | `alibabacloud-ecs-instance-state-diagnosis` |
| Base files such as the default shell are missing and every command fails | Operating system damage that needs an offline disk repair | `alibabacloud-ecs-linux-os-troubleshooting` |
| A passkey, security key, fingerprint or face logon to a third-party website | WebAuthn on a third-party platform; an ECS instance has no biometric hardware or matching operating system framework for it | The third party's own documentation |
| Overdue balance, a released instance, resources invisible in this account | Account or commercial scope, not guest credentials | Account and billing support |
| Adding, deleting or re-scoping a security group rule | A network access policy change | The security group documentation and console |
| A third-party terminal-services activation script or cracked licensing | An unlicensed path | The vendor-licensed Remote Desktop path only |
| The Workbench file upload experience | Console product experience | Workbench support |
| The aftermath of a brute-force campaign, deeper incident response | Security incident handling | The security incident skills |

## How to hand off

1. Attach the evidence, do not attach an opinion. The report's `EVIDENCE
   COLLECTED`, `INSTANCE FACTS` and `CLOUD ASSISTANT CHANNEL` blocks go with the
   case, including the steps that returned nothing.
2. Say the boundary in one sentence, using the wording in the table. A customer
   accepts a handoff they can understand; they argue with a vague escalation.
3. Keep the credential branch closed until the other tier reports back. Running
   more credential checks against a wedged or damaged guest wastes the customer's
   change window.
4. Where the handoff involves a restart, an offline repair disk or any other
   change, the snapshot gate in `keypair-and-credential-guidance.md` applies
   first, and it is a human step.

## Two boundaries that need careful wording

**Third-party passkey logon.** Recognise it on the trigger words (passkey,
security key, fingerprint, face logon) and stop before the diagnostic flow: this
tier's "key pair" has nothing to do with a platform authenticator. Say what an
ECS instance does not have (a biometric sensor, a platform authenticator, the
target site's own acceptance rules), point at the third party's documentation,
and do not offer an unverified workaround. A workaround that raises an
expectation the platform cannot meet costs more trust than a clean boundary.

**Operating system damage.** The signature is a credential failure paired with
commands that cannot start at all: a missing default shell, every remote command
failing, a password reset that dies at its key pair step. See the
`/bin/bash` row in `error-signatures.md`. Do not keep testing keys; name the
damage, apply the snapshot gate, and hand off.

## What never gets handed off

Questions this tier owns outright and answers from its own references: key pair
naming and lifecycle facts, the effect condition of a binding, why a private key
or a password cannot be queried back, how console passwordless logon works, the
Windows session ceiling and lockout behaviour, multi-user key logon on Linux, and
what a Cloud Assistant status means. Those are in `faq.md`,
`keypair-and-credential-guidance.md` and `login-decision-tree.md`.
