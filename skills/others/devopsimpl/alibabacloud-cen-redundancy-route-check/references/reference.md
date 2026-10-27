# CEN Redundancy Route Check: Detailed Algorithm

## 1. Data Model

Aggregate the following evidence keyed by `(region, route table, destination CIDR)`:

- Topology: CEN, TR, Peer/VPC/VBR/VPN Attachments
- Routes: status, type, origin, next-hop attachment, next-hop resource ID/type
- Policies: direction, priority, match conditions, Permit/Deny, attribute changes
- Exceptions: permissions, API, pagination, region, resource state, and conflicting routes

Deduplicate all objects by stable resource ID; when the same resource appears on different pages, merge its state and evidence sources.

## 2. CEN Version Identification

1. Query the CEN instance and its attached network instances, recording each child instance's region.
2. Query all TRs of the CEN, group them by `RegionId`, and record each TR's `Type`.
3. Decide the version per target region: if the region has an `Enterprise` TR, inspect it with the CEN 2.0 workflow.
4. If the region has only a `Basic` TR or no TR, use the CEN 1.0 workflow for that region only when the CEN, attachment, and TR queries all succeeded and pagination is complete.
5. Output "Unable to confirm" for a region when permissions are insufficient, a query failed, the scope is incomplete, or a TR `Type` is missing or unrecognized.

Never infer the CEN version from a single empty list or from the mere presence of a TR, and never apply the version of one region to another: a CEN may use Enterprise TRs in some regions and CEN 1.0 attachments (with a Basic TR or none) in others.

## 3. CEN 2.0 Topology Traversal

For each TR:

1. Query Peer Attachments to build the cross-region TR adjacency graph.
2. Query VPC, VBR, and VPN Attachments, recording their status and owning resources.
3. Locate the TR and region that own the target VBR.
4. Traverse all related remote TRs from that TR along Peer Attachments.
5. Collect the VPCs attached to related TRs to form the set of VPCs to inspect.

When an Attachment is not `Attached` or a TR is not `Active`, emit a warning and do not count it as an available redundant path.

## 4. TR Route Table Analysis

For each related TR:

1. Query all system/custom route tables.
2. Query all route entries with `All` status for each table.
3. Filter prefixes equal to or more specific than the user-confirmed IDC CIDR.
4. Aggregate Active/Standby/Candidate/Rejected/Prohibited routes per destination CIDR.
5. Resolve the next-hop Attachment and map it back to the VBR/VPN/Peer/VPC resource.

In cross-region scenarios, the next hop from a remote TR to the IDC usually appears as a Peer/TR path; follow the topology to the VBR/VPN in the target region instead of requiring the remote TR to show the VBR directly as the next hop.

## 5. VPC Route Table Analysis

1. Query the system and custom route tables of each related VPC.
2. Query all IDC-prefix routes of each route table.
3. Record route type, status, next-hop type, and next-hop ID.
4. Cross-validate VPC next hops against TR Attachments, TR routes, and Peer paths.
5. Report missing/abnormal when the VPC side lacks an IDC route, the next hop is invalid, or it points to an unexpected resource.

When `DescribeRouteEntryList` does not provide complete PBR matching semantics, only output "Manual confirmation required"; it cannot prove the absence of PBR.

## 6. CEN 1.0 Analysis

1. Query CEN regional routes with `All` status for each region of the attached instances.
2. Aggregate primary, candidate/standby, and rejected/prohibited paths per IDC prefix.
3. Identify VBR/VPN next hops using the attached network instances.
4. For every VPC child instance attached in the region, query its route tables and IDC-prefix routes (section 5), then call `DescribeRouteConflict` with that VPC route table and each IDC CIDR.

CEN 1.0 regions never run any TR Attachment, TR route table, or TR route entry query, even when a Basic TR exists.

## 7. Route Map Impact

For all policies of the target CEN and related regions:

- `Deny` matching the standby VBR/VPN, the IDC CIDR, or a related region: high risk.
- Attribute changes that make two expected equal-cost paths no longer equal: load-balancing risk.
- Priority changes consistent with the confirmed active/standby design: record as active/standby evidence, but still verify the standby route can be learned.
- Policy scope or match conditions cannot be fully determined from the response: mark as "Unable to confirm".

## 8. Redundancy Verdict

### Dual-VBR ECMP

The same IDC CIDR MUST have at least two available, expected VBR paths that are not prohibited by policy. Two Attachments alone do not prove the routes are equal-cost.

### Dual-VBR Active/Standby

Requires both valid evidence of the primary path and candidate/standby routes of the standby VBR or verifiable policy evidence. If the standby path only appears after the primary route is withdrawn and the API cannot prove it, the verdict is "Failover verification required".

### VBR + VPN Active/Standby

Must map to one VBR path and one VPN path, and verify Attachment status, TR/CEN routes, and the VPC down-cloud path. Missing evidence on either side means redundancy cannot be judged complete.

## 9. Error Propagation

- A single VPC query fails: that VPC and the end-to-end verdicts depending on it are "Unable to confirm".
- A single TR/Peer query fails: all regional links affected by it are "Unable to confirm".
- The Route Map query fails: never report "No impacting policy found".
- A critical topology query fails: the overall result must never be "All healthy".

## 10. Report Wording

Distinguish the following states:

- `Healthy`: evidence is complete and matches the user-confirmed expected mode.
- `Missing`: expected resource or route evidence clearly does not exist.
- `Abnormal`: rejected, prohibited, conflicting, unexpected next hop, or unhealthy state exists.
- `Unable to confirm`: permissions, API, pagination, or returned fields are insufficient.
- `Manual confirmation required`: PBR or failover behavior cannot be proven by read-only configuration queries.
