# Decision tree and symptom mapping — alibabacloud-ecs-idc-address-query

Read-only knowledge for routing a customer's phrasing to the correct handling.
Physical machine-room location is **not visible inside the guest OS**, so this
skill never enters the instance; it uses only cloud reads plus disclosure /
handoff wording.

## Customer symptoms this skill serves

- "Where is my ECS instance physically located?" / "which data center / server
  room" / "physical location" / "machine room address".
- "Give me the data center address for instance `i-...`" (often for MLPS /
  class-protection, drug-supervision, or ICP filing forms).
- "What city / region / availability zone hosts this public IP?"
- "I need proof of the server's physical location."
- A location query that failed with `NoPermission` / `ImplicitDeny`.

## Decision tree (mirrored by `scripts/axes/idc_address_query/idc_address_query.py`)

1. **Is there an instance id or a public IP?**
   - No → emit input guidance (what identifier is needed, where to find it,
     and to act from the owning account). `STATUS: FAIL`, next action: re-run
     with an identifier. Do not query, do not guess.
2. **Does the resource belong to the current account?**
   - The credential is resolved by the default chain (`GetCallerIdentity`).
   - Instance not found in any scanned region → emit the cross-account refusal
     plus the released-instance note. `STATUS: DEGRADED`, next action: confirm
     the id or open a ticket from the owning account.
3. **Instance found** → read `RegionId`, `ZoneId`, `Status` and the IP
   attributes via `DescribeInstances` (optionally confirmed by
   `DescribeInstanceStatus`). Output the region/zone and the **public city-level
   name** of the region, then append the confidentiality, safe-use and
   ticket guidance. `STATUS: OK` (or `DEGRADED` if any read failed mid-scan).
4. **Is the real ask a document, a finer address, ISP/MAC, or another
   product?** → route via the handoff matrix in `references/idc-address-query__handoff-and-inputs.md`.

## Evidence rules (anti-hallucination)

- Only fields returned by the read APIs are stated. The public city name is
  looked up from the embedded region table; unknown regions are reported by
  raw id.
- A district/street-level address, facility name, or rack position is **never**
  produced. When asked, state the disclosure boundary and point to the ticket
  channel.
- Do not cite documentation URLs that are not present in this package. If a
  help-doc link is needed but unverified, say so and route to the ticket
  channel instead of inventing a URL.

## Region / zone selection reads

- `DescribeInstances` requires `RegionId`; when the customer did not supply a
  region the script scans the embedded public region table and reports how many
  regions it searched.
- Zone availability (the "which regions/zones can I buy" phrasing) uses
  `DescribeAvailableResource` with a required `DestinationResource`; stock
  categories are echoed with the public meanings embedded in
  `scripts/axes/idc_address_query/_constants.py`.

## Output contract

Every run ends with two machine-checkable lines the agent must relay verbatim:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <human guidance, or "None">
```

- `OK` — located at least one resource, no degraded reads.
- `DEGRADED` — partial: some region reads failed, or the resource was not
  found under this account (refusal/handoff wording given).
- `FAIL` — could not proceed: missing identifier, or authorization /
  credential failure.

All guidance is human-only. This skill never applies a change, never runs a
command inside the instance, and never fabricates a confidential address.
