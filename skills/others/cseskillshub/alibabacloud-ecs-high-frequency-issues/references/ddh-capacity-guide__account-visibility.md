# Account / Region Visibility Pre-Check (Cluster E1)

Rule-based answers for "the engineer says my instance is not under this account",
"why can't you see my instance", and "I filed the ticket from the wrong account".
This is a native strength of the read-only APIs: a query that returns empty is a
precise, immediate finding.

Verification date: 2026-08 (per the tier requirements document).

## The rule

- Read-only Describe APIs only see resources inside the CURRENT credential account
  AND the specified `RegionId`.
- An empty result therefore does NOT prove the instance does not exist. It means the
  instance is not visible under this account/region combination.
- The two common causes:
  1. The ticket was filed from a different account than the one that owns the
     instance (very common when a customer has multiple accounts).
  2. The wrong region was queried (the instance lives in another region).

## How the entry script applies it

- `ddh_capacity_guide.py` calls `DescribeInstances` (and `DescribeInstanceStatus`)
  with the supplied `RegionId` and instance id(s).
- If the result is empty, the script reports the visibility boundary honestly and
  routes to this guidance: re-check with the owning account's credential and the
  correct region. It never fabricates instance data and never concludes "the
  instance does not exist".
- The account UID is auto-derived from the credential via `sts get-caller-identity`
  and declared in the report, so the customer can immediately see WHICH account was
  queried.

## What this skill can and cannot confirm

- CAN (read-only): state definitively that the target instance is not visible under
  the current credential account + queried region, and name the account UID that was
  queried.
- CANNOT: see instances owned by another account (cross-account visibility is a hard
  boundary), or confirm the real health of an instance that is not visible. Once the
  customer re-runs under the correct account/region, the other guidance modules
  apply.

## Guidance to the customer

1. Confirm the account UID that owns the instance (in the ECS console of the owning
   account) matches the UID this skill reported.
2. If they differ, re-run the diagnosis using the owning account's credential.
3. If the account matches but the instance is still not found, verify the region -
   the instance id is region-scoped, so query the region where it was created.

## Sources

- Real support tickets in this tier (the instance was not under the ticket-filing
  account, so the engineer could not investigate until the customer re-consulted
  from the owning account).
