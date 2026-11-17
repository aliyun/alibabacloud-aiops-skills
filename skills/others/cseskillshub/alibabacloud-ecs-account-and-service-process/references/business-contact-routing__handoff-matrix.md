# Hand-off matrix

This skill owns the contact-routing segment only. Technical symptom words are transfer signals,
never triggers this skill acts on, and it never re-implements another skill's diagnostics.

| Customer symptom | Owning capability | What this skill does | Transfer wording |
|---|---|---|---|
| Disk space or inode usage, cleanup decisions | `alibabacloud-ecs-disk-capacity` | Records the ask, routes the technical part away | "The core of this request is in-guest usage, which the capacity capability handles, including read-only diagnostics inside the instance. I am transferring that part." |
| Scale-out finished but the partition or volume did not grow | `alibabacloud-ecs-disk-expand-diagnosis` | Same | Same wording with the symptom name swapped |
| Instance will not come up, or is held in a transitional state | `alibabacloud-ecs-instance-state-diagnosis` | Same | Same wording with the symptom name swapped |
| Disk latency or IOPS below the purchased level | `alibabacloud-ecs-disk-io-diagnosis` | Same | Same wording with the symptom name swapped |
| Refund, unsubscribe, downgrade, invoice, account-entity change | Human billing or business owner | States that no automatic path exists, gives the manual acceptance route plus the read-only material pack | "This is a commercial action and cannot be executed by an agent. Here is the manual route, with your resource context already prepared." |
| Technical fault, but the customer insists on a phone conversation | This skill plus the owning diagnosis skill | States that self-service diagnosis exists, then gives the channel guidance | "Self-service diagnosis for this symptom does exist, so you can choose it. For a conversation, here is the human route." |

## Why guest and reversible-write capability is absent here

The batch decisions about in-guest read-only diagnostic commands, the command allowlist,
"take a snapshot before any cleanup", Windows coverage and monitoring reads all target
disk-capacity symptoms. This tier has a read-only operation type and a contact-routing symptom
axis, so none of those clauses are implemented:

* Command execution inside an instance is a write-class capability and is out of scope.
* There is no cleanup branch, so the snapshot-first rule has nothing to guard.
* Monitoring reads would answer a usage question, which belongs to the capacity skill.

If ticket review later shows that this tier's tickets contain capacity-handling steps, the
correct response is to route those steps to the capacity skill, not to widen this skill's
permissions.

## Boundary of the material pack

The pack is prepared context, never a decision: which instances the ask concerns, their
returned power state and type, the account tag, and the customer's own words. Eligibility,
commitments, negotiation outcomes and any state change stay with the human owner.
