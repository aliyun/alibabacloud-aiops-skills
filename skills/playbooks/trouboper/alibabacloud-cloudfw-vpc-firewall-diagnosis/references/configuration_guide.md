# VPC Firewall Configuration Guidance

This document provides text-only configuration guidance for VPC firewall scenarios. The skill must not execute configuration changes.

## Preconditions

- Cloud Firewall edition supports VPC firewall.
- The required VPC firewall quota is available.
- An Enterprise Edition transit router exists and is running.
- The VPC is attached to the transit router.
- The user has confirmed the region, CEN instance, and target VPC information.

## Console-only Guidance

When a remediation requires configuration, provide console navigation and parameter checklists only. Do not provide executable write commands.

Typical manual items:

- Add or adjust a route entry in the CEN console.
- Add a VPC to the firewall protected scope.
- Review or adjust ACL policies in the Cloud Firewall console.
- Clean residual empty route tables after route revoke closure.

## Route Remediation Checklist

For a missing route, ask the user to review these fields in the CEN console:

- Route table ID.
- Destination CIDR.
- Next-hop type.
- Next-hop resource ID.
- Route name or description.
- Business owner approval.

## ACL Remediation Checklist

Before closure or re-enable operations, ask the user to review:

- Existing allow and deny policies.
- Source and destination CIDR ranges.
- Protocol and port scope.
- Policy priority and hit expectation.
- Whether temporary allow policies are needed during a maintenance window.

## Safety Requirements

- Do not output complete create, modify, or delete CLI commands.
- Do not include concrete production identifiers in write-operation examples.
- Do not run any write action through the terminal.
- Keep all recommendations as text-only guidance.
