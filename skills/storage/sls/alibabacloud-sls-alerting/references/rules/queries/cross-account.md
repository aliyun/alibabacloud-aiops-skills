# Cross-account alert queries

An advanced, optional feature for rules that query data in another Alibaba
Cloud account. Normally omit `configuration.queryList[].roleArn`; a different
Project or region alone does not require adding it. Preserve an existing role
when updating unrelated settings.

## Configure a cross-account source

Account A owns the alert rule; account B owns the queried data.

1. Resolve both account IDs and the source Project, region, and Store in B.
2. Obtain a RAM role in B whose trust policy allows A's SLS service to assume
   it. The role needs log query and index access to the source; include discovery
   permissions if needed. Use the [official cross-account authorization guide](https://help.aliyun.com/zh/sls/configure-access-control-policies)
   for trust and access-policy examples.
3. Read the actual role ARN from B. Set it on each `queryList` entry that reads
   B's data; set that entry's `project`, `region`, and `store` to the source.
   Rule commands still target the owning Project in A.
4. If the configuring caller is a RAM user, check the required `ram:PassRole`
   permission scoped to that role ARN.

Reuse an appropriate role. Creating or changing RAM roles, trust, or policies
requires the user's explicit request; if the role is unavailable, report the
missing ARN or authorization. Caller API permissions are covered separately
in [RAM policies](../../ram-policies.md).

## Verify runtime access

Confirm the role exists in B, trusts A's SLS service, and can read the selected
source. A query under the CLI profile does not verify this role's permissions.
Use evaluation evidence from [alert history](../../diagnosis/diagnose.md#start-with-the-incident) when runtime
verification is requested; otherwise report it as unverified.

For `GetQueryRoleTokenError`, check the configured ARN, role existence, and
trust policy first, then the role's source permissions. Do not switch profiles
or broaden permissions implicitly.
