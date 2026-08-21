# RAM Policies and Cloud Authorization

## No Cloud Authorization Required

This skill does **not** invoke any Alibaba Cloud OpenAPI. All probing is
performed against the public probing platform `boce.aliyun.com` over plain
anonymous HTTPS:

- No Alibaba Cloud account, AccessKey, or STS token is needed.
- No RAM role, RAM policy, or service-linked role is required.
- No `sts:AssumeRole` or identity verification step is performed.

## Implications

| Concern | Status |
|---------|--------|
| RAM policy to attach | None — there is nothing to authorize |
| Minimum permission set | N/A (no cloud API surface is touched) |
| Credential configuration | None; never ask the user for cloud credentials |
| Credential leakage risk from this skill | None — the scripts carry no cloud secrets |

The only external communication is the anonymous web session used to
submit and poll probes on the public platform, identified by a
skill-specific User-Agent header (see the Observability section in
SKILL.md).

If a future version of this skill starts calling Alibaba Cloud OpenAPI,
this document and `related_apis.yaml` must be updated accordingly before
release.
