# Security Rules Reference

This document lists security rules and safety constraints for VPC firewall diagnosis.

## Precheck Security Rules

### Region Support

The VPC region must support VPC boundary firewall. If the region is unsupported, explain the limitation and guide the user to the console for manual product or region review.

### Transit Router Requirement

An Enterprise Edition transit router must exist and be in a healthy state. Basic Edition transit routers are not supported for the relevant VPC firewall scenarios.

### Route Safety

Before provisioning or closure, check for route conditions that may block or affect the operation:

- Static routes in candidate route tables.
- Rejected routes caused by route conflicts.
- ECMP route sets with incomplete next-hop scope.
- Route map inconsistency across route tables.
- Missing rollback target routes before closure.

### ACL Safety

Before closure and later re-enable operations, review ACL state:

- Whether any ACL policy exists.
- Whether deny policies may affect traffic after session changes.
- Whether temporary allow policies are required during a maintenance window.

## Operational Safety

The skill must remain read-only:

- Allowed: describe, list, get, lookup, check, query, search, and test read-only operations.
- Forbidden: create, modify, delete, attach, detach, start, stop, enable, disable, add, remove, associate, disassociate, grant, revoke, reset, replace, authorize, submit, apply, register, deregister, publish, withdraw, and refresh operations.

## Credential Safety

- Never hardcode AccessKey values.
- Never hardcode a concrete profile name.
- Never extract credentials from local files.
- Always ask the user which CLI profile to use.

## Reporting Safety

- Do not expose unnecessary resource inventories.
- Avoid printing full request payloads unless required for diagnosis.
- Prefer masked or summarized evidence when possible.
- Provide remediation as text-only guidance, not executable write commands.
