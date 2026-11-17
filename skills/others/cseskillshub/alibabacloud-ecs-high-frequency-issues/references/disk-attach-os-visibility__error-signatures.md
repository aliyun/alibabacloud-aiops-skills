# Signatures: what the customer says, what to check first

## Wording the customer produces

These are the sentences that mean this skill is the right one. They are symptom wording,
not root causes; the verdict comes from the readings, not from the phrase.

| What the customer says | Usually broken link | First check |
| --- | --- | --- |
| "I bought a data disk, it is not in the server" | 4 or 5 | Placement from `DescribeDisks`, then `lsblk -f` |
| "The disk is attached but I cannot see it" | 3, 4 or 5 | `lsblk` for a device of that size |
| "`df -h` does not show the new disk" | 4 or 5 | `lsblk -f`: an empty filesystem column means it was never initialised |
| "Where do I configure the mount point, the option is grey" | nothing | Placement is already finished; the work is inside the guest |
| "There is no detach option for this disk" | 2 | The disk is not placed on anything, so placement, then removal |
| "My files are gone after I mounted the disk on /data" | 5, by design | `findmnt` on that path, then explain hiding, then manual unmount to confirm |
| "The disk is missing after I reinstalled the system" | 5 or the name changed | Guest family, then `lsblk -f`, then the recorded device name |
| "DiskPart unable to set the disk online because the disk cannot be found" | Windows volume state | Recovery point first, then human repair; no repair command is issued here |
| "I extended the disk but the size did not change" | out of scope | Capacity growth that has not reached the partition belongs to disk expansion |

## What this skill does not claim

No catalogue of platform error codes is asserted for this tier. Codes are read from the
response when one arrives and are quoted exactly as returned; the report never names an
error code it did not receive, and the agent never maps a code to a cause from memory.
When a call fails without a code, the text `CliInvocationFailed` plus the first line of
output is what is reported.

Two transport-level strings are worth recognising because they change the next action:

| Text seen | What it means here |
| --- | --- |
| `is not a valid api` | The CLI build does not know that action. Stop, report the product and version being called, and do not improvise a different action name. |
| `NoPermission` or `ImplicitDeny` | The credentials are valid but the policy is not. State which action was refused and hand over the statement from [ram-policies.md](ram-policies.md). |

A timeout is a transport fact, not a diagnosis. One call per action is retried with
backoff, and if it still fails the report says which link could not be evaluated and why,
instead of filling the gap with an assumption.

## Reading a diagnostic that returned nothing

An empty guest listing is not evidence that the disk is gone. Before concluding link 3,
check that the delivery actually ran: an absent or outdated Cloud Assistant agent yields
no output at all, and `DescribeInvocations` reports history rather than live state. The
correct conclusion in that case is `OS_READINGS_UNAVAILABLE`, and the correct next action
is to ask the customer to run one approved command themselves and paste it, which is also
the fallback when the customer declines the delivery.
