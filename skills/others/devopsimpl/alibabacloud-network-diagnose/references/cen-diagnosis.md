# CEN and Transit Router Diagnosis

Use this reference when the route next hop is CEN/TR, when VPCs are attached to
the same CEN, or when cross-region private connectivity fails.

## Required Checks

1. Confirm both VPCs are attached to the expected CEN.
2. Identify the Transit Router in each region.
3. Find VPC attachments for source and destination VPCs.
4. Check TR route table association for both attachments.
5. Check TR route propagation for both attachments.
6. Check forward and return route entries in the associated TR route tables.
7. Check VPC route tables on both sides.
8. Check NACLs on all TR VPC attachment zone-mapping VSwitches.
9. Check CEN route maps when routes are missing or rejected.

## Decision Logic

- `association_missing`: the attachment is not associated with the route table
  used for forwarding.
- `propagation_missing`: the attachment does not propagate routes to the route
  table.
- `route_missing`: no route matches the destination CIDR or IP.
- `route_conflict`: a more specific route points to an unexpected next hop.
- `route_map_deny`: a route map may reject or modify the route.

## CEN Route Learning Scope

CEN-propagated routes can appear in all route tables in a VPC, including system
and custom route tables. Do not assume that placing ECS and TR attachments in
different VSwitches avoids CEN route interference.

Both `AutoPublishRouteEnabled` and `RoutePropagationEnable` must allow route
publication before CEN routes appear in VPC route tables.

## Cross-Region Transit

CEN cross-region routes cannot transit through an intermediate region. If a
Beijing VPC and a Shenzhen VPC are both attached to a Shanghai TR, explicit
Beijing-Shenzhen cross-region connectivity is still required.

## TR Zone VSwitch NACLs

Traffic does not always traverse the nearest zone VSwitch. Check all zone
mappings on both source and destination VPC attachments:

- source-side zone VSwitch NACLs can affect return traffic entering the source
  VPC.
- destination-side zone VSwitch NACLs can affect forward traffic entering the
  destination VPC.

Missing one side can leave connectivity broken after another issue is fixed.
