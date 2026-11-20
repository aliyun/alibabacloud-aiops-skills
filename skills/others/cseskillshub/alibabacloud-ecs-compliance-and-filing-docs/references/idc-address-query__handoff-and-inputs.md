# Inputs and handoff — alibabacloud-ecs-idc-address-query

## 1. Required inputs

To resolve a physical deployment location, exactly one of these resource
identifiers is required:

- **ECS instance id** — format `i-` followed by letters/digits; up to 100 per
  run; both `--instance-id i-...` repeated and a comma-separated value are
  accepted. Visible in the ECS console under **Instances** (Instance ID
  column).
- **Public IP address** — the instance's public IP or EIP. Visible under the
  instance's public IP / EIP column, or in the **Elastic IP Address** console.

Supporting, optional inputs:

- `--region` — narrows the read to one region and avoids a multi-region scan.
- Run the query with the credential of the account that **owns** the resource;
  resources of other accounts are not visible and are handled with the
  cross-account refusal wording, not by guessing.

If neither identifier is supplied, the entry script returns
`STATUS: FAIL` and prints the input guidance instead of querying. This is the
deliberate fix for the ticket pattern where the request stalled and closed
because no instance id was ever provided.

## 2. Handoff matrix

These adjacent requests are recognized and routed to another skill or to a
human channel. This skill does not answer them from memory. The matrix is the
single source mirrored by `scripts/axes/idc_address_query/_constants.py` (`HANDOFF_RULES`).

| Adjacent request | Route to | Why not handled here |
|---|---|---|
| ICP filing process, filing blocked/status | `alibabacloud-ecs-icp-filing-guide` | The filing workflow is a different vertical; this skill only supplies the location evidence to attach. |
| Recovering a released/expired instance or its data; retention windows | the instance lifecycle / data-retention skill in the catalog | Location of released instances is not queryable; recovery is a lifecycle topic. |
| Stamped location certificate, lease contract, official paper document | offline human support (senior engineer via the ticket channel) | Such documents must be issued officially; a read-only tool cannot produce them. |
| Physical location of RDS / Redis / SLB / any non-ECS resource | that product's console / support channel | Scope is ECS instances only. |
| ISP / carrier access information, MAC-level disclosure | the ticket channel | No verified public data source exists in this iteration; the tool states this honestly. |
| Purchase, orders, contract or pre-sales region selection logistics | console purchase page / pre-sales channel | Commercial logistics stay with sales; this skill only reports zone availability as public information. |

## 3. Disclosure boundary (customer-facing)

- This skill reports **region, availability zone, and the public city-level
  geographic name of the region** only.
- **District-level or street-level data-center addresses, facility/building
  names, and building/floor/rack/slot positions are confidential.** They are
  released only by official support through the ticket channel after ownership
  verification. The tool never outputs or guesses them, even when a customer
  pushes for "the exact street" or "the rack".
- The city-level names come from the embedded public region table in
  `scripts/axes/idc_address_query/_constants.py`. A region absent from that table is reported by raw
  region id only; no location is inferred.
