# The encryption option makes the order fail - what to check, in order

Applies when the customer ticks the encryption option while provisioning a disk or an
instance and the order is refused, or when a key cannot be picked in the console. This is a
**checklist plus read-only evidence** flow: the skill reads what is readable, the customer
pastes back what only they can see, and the customer performs every fix.

## 1. Ask for these two things first

1. The exact text of the failure, copied - not paraphrased.
2. A screenshot of the order panel showing the region, the disk category, the encryption
   option and the key selector.

Neither the order nor the console session is visible to this skill's reads, so the pasted
text is the primary evidence. Record it verbatim, masked.

## 2. Read what is readable

```bash
python3 scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id <region> --instance-id <id> --encrypted-only
python3 scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id <region> --all-disks --format json
```

What this proves, and what it does not:

| Read result | What you may say | What you may not say |
|---|---|---|
| Other disks in the region are already encrypted | "Encryption has worked in this account and region before, so the feature itself is reachable." | "Then the key and the rights are fine." The failing order may use a different key or a different identity |
| No disk in the region is encrypted | "This is the first encrypted disk in this region, so the key and permission path has not been exercised here." | "Nothing is wrong with the account." |
| The region returns nothing at all | Wrong region or wrong profile - confirm both, then re-read | Any conclusion about encryption |

## 3. The checklist, in this sequence

1. **Region match.** A key lives in one region. A key prepared in another region will not
   appear in this region's selector. Ask the customer to check the region shown in the order
   panel against the region shown in the key list.
2. **Service key or customer-managed key?** Have the customer retry once with the service-key
   form of the encryption option (no key chosen). If that succeeds, the failure is on the key
   or the rights side, not on the disk category or stock. If it still fails, go to 6.
3. **A usable key must already exist.** The customer-managed path never makes a key on the
   fly. The customer confirms in the key-management console that a key exists in this region
   and is in a usable state, and notes its id or alias to compare with the console selection.
   This skill does not read key objects; the customer's console view is the evidence.
4. **Rights of the identity placing the order.** The RAM user or role that places the order
   must be allowed both the disk-order rights and the use of that key. Ask the customer to
   retry with an account-level identity once: if that works, the sub-identity's policy is the
   gap. Report the refusal literals exactly as returned - `NoPermission` or `ImplicitDeny` -
   and give the read-side snippet from `ram-policies.md`, while making clear that the
   order-side rights belong to the customer's own policy set, which this skill cannot read.
   Permission docs to cite:
   `https://help.aliyun.com/zh/ecs/user-guide/encryption-related-permissions.md`.
5. **Cross-account or alias confusion.** An id copied from another account, or an alias that
   resolves in a different region, reads as "no such key". Ask the customer to pick the key
   from the console list rather than typing an id.
6. **Account-state blockers.** An overdue balance or a real-name/qualification requirement can
   refuse an order independently of encryption. That is a billing question - hand it off per
   `handoff-matrix.md`; this skill cannot read an invoice.
7. **Isolation trick.** Same zone, same category, same size: order once with the encryption
   option off. If that succeeds, the difference is the encryption path and nothing else.
   State this as an experiment result, not as a root cause.

## 4. The proven fallback

When the customer needs the disk now: complete the order **without** encryption, then move the
data onto an encrypted disk provisioned later, following Path A in `encryption-basics.md`.
Say explicitly that the unencrypted intermediate disk is a temporary object and that the data
on it is not protected at rest until it lives on the encrypted disk. This is the exact route
that resolved the ticket-derived case behind this tier, so it is a supported answer - not a
workaround to be whispered.

## 5. What this skill will not do

- It will not invent or translate an error code. If the customer's text contains no code, say
  "no code was returned in what you pasted" and work from the text.
- It will not issue any order, retry it on the customer's behalf, or produce a console command
  line that changes anything.
- It will not read the account's key list, key policy, orders or invoices: those are not in its
  permission set (`ram-policies.md`).
- It will not run anything inside the instance.

## 6. Closing the loop

After the customer's fix, re-read and show the before/after rows:

```bash
python3 scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id <region> --disk-id <new-disk-id>
```

Report `STATUS: OK` only when the new disk's encryption field came back from the read. If the
field is absent, report `DEGRADED` with the console check from `query-recipes.md`.
