# Cross-account alert queries

An advanced, optional feature for rules that query data in another Alibaba
Cloud account. Normally omit `configuration.queryList[].roleArn`; a different
Project or region alone does not require adding it. Preserve an existing role
when updating unrelated settings.

## Configure a cross-account source

Account A owns the alert rule; account B owns the queried data.

The role in B trusts A's SLS service and grants access to the selected source's logs
and indexes, with discovery permissions when needed. The
[cross-account authorization guide](https://help.aliyun.com/zh/sls/configure-access-control-policies)
provides trust and access-policy examples.

Each query reading B's data uses that role's actual ARN in `roleArn`, with `project`,
`region` and `store` identifying the source. Rule operations still target the owning
Project in A. A RAM user configuring the role reference also needs `ram:PassRole`
scoped to that ARN.

Reuse an appropriate role. Creating or changing RAM roles, trust, or policies
requires the user's explicit request; if the role is unavailable, report the
missing ARN or authorization. Caller API permissions are covered separately
in [RAM policies](../../ram-policies.md).

## Verify runtime access

Role existence, trust and source permissions determine runtime access. A query under
the CLI profile does not establish this role's permissions;
[alert history](../../diagnosis/diagnose.md#start-with-the-incident) can provide evaluation evidence.

For `GetQueryRoleTokenError`, check the configured ARN, role existence, and
trust policy first, then the role's source permissions. Do not switch profiles
or broaden permissions implicitly.
