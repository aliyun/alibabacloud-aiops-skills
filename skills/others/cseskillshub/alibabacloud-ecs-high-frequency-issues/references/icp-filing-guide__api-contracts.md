# API Contracts (verified, read-only)

Every OpenAPI action this skill invokes, with the request parameters and
response fields the scripts actually consume. All actions were verified
against the live API metadata for this tier; nothing outside this list may be
called. The shared layer `scripts/areas/icp_filing_guide/_cli.py` enforces the whitelist at runtime
and refuses any other action before a subprocess is spawned.

Invocation channel: the `aliyun` CLI as a subprocess (argument-list form,
never a shell string), one per-call timeout, automatic retry with linear
backoff on transient errors (throttling / 5xx / timeout), and credential
masking on every error string. Command style per product:

- `ecs` and `vpc`: plugin mode - lowercase-hyphenated command names,
  e.g. `aliyun ecs describe-instances --biz-region-id cn-hangzhou`.
- `sts`: CLI plugin mode - lowercase-hyphenated commands,
  e.g. `aliyun sts get-caller-identity`. `_cli.py` translates the API action
  name to the plugin command form automatically.

Every call carries `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<session-id> skill-version/<skill-version>`
(see the Observability section of SKILL.md).

## 1. sts GetCallerIdentity (plugin: `aliyun sts get-caller-identity`)

- Version: 2015-04-01. Endpoint: `sts.aliyuncs.com` (pinned by `_cli.py`).
- Request: no parameters.
- Consumed response fields: `AccountId` (UID traceability label), `Arn`,
  `IdentityType`.
- Used by: `scripts/areas/icp_filing_guide/sts_token.py`; `_cli.resolve_account_uid()` inside
  `icp_filing_check.py` (eligibility and triage modes).
- Failure handling: in `icp_filing_check.py` a failed identity call prints
  `[WARN] caller identity unavailable`, keeps the report's `uid_label` as
  `unresolved`, and degrades the run (`STATUS: DEGRADED`) when the other
  queries still succeeded. `scripts/areas/icp_filing_guide/sts_token.py` instead exits non-zero with
  the error code and guidance to verify the default credential chain with `aliyun sts get-caller-identity` - never to hand over
  credentials.

## 2. ecs DescribeInstances

- Version: 2014-05-26. Regional endpoint resolved by the CLI from `--region`.
- Request parameters actually sent:
  - `RegionId` (required by the API).
  - `PageSize` (50) and `PageNumber` for pagination (`_cli.paginate_page_number`,
    guardrail 20 pages).
  - `InstanceIds` - JSON array string, e.g. `'["i-bp1example"]'` (locate one
    instance in triage mode).
  - `PublicIpAddresses` - JSON array string with one fixed public IP (locate
    the instance a domain points at, triage mode).
  - `EipAddresses` - JSON array string with one EIP, tried when the fixed-IP
    filter returns nothing, followed by a local match against the returned
    `PublicIpAddress`/`EipAddress` fields of every instance in the region.
  - eligibility mode sends only `RegionId` + pagination (account-wide scan).
- Consumed response fields (per instance in `Instances.Instance[]`):
  `InstanceId`, `InstanceName`, `RegionId`, `Status`, `OSNameEn` (fallback
  `OSName`), `InstanceChargeType`, `ExpiredTime`, `InternetMaxBandwidthOut`,
  `PublicIpAddress.IpAddress[]`, `EipAddress.IpAddress`,
  `SecurityGroupIds.SecurityGroupId[]`.
- Used for:
  - eligibility mode: the account-wide scan that reproduces the support-side
    "we checked your account" step (mainland node / subscription term /
    public bandwidth);
  - triage mode: locating the target server and its public endpoints.
- Failure handling: a region that fails is recorded with its API error code (a
  `[WARN]` line plus an entry in the report's `errors[]`, and the region is
  listed in `regions_with_failures[]`); the remaining regions are still
  scanned. When the report says a region failed, `NONE_FOUND` is never read as
  "the account holds no server". When the code is `NoPermission` or
  `ImplicitDeny` the report names `ecs:DescribeInstances` and points at
  `references/ram-policies.md`.

## 3. ecs DescribeSecurityGroups

- Version: 2014-05-26.
- Request parameters actually sent: `RegionId`, `PageSize` (50), `PageNumber`.
- Consumed response fields (per group in `SecurityGroups.SecurityGroup[]`):
  `SecurityGroupId`, `SecurityGroupName`.
- Used for: labelling each attached group with its name in the triage report.
  The group IDs that are actually inspected come from the instance record's
  `SecurityGroupIds`; this call only supplies the names shown next to them.
- Failure handling: degrades with a `[WARN]` and an `errors[]` entry; triage
  continues unchanged, because rule evaluation only needs the group IDs from
  `DescribeInstances`.

## 4. ecs DescribeSecurityGroupAttribute

- Version: 2014-05-26.
- Request parameters actually sent: `RegionId`, `SecurityGroupId`,
  `Direction` = `ingress`, `MaxResults` (1000) and `NextToken` pagination
  (`_cli.paginate_next_token`, guardrail 20 pages).
- Consumed response fields (per rule in `Permissions.Permission[]`):
  `Direction`, `IpProtocol`, `PortRange`, `Policy`, `Priority`,
  `SourceCidrIp`, `Ipv6SourceCidrIp`, `SecurityGroupRuleId`, `SourceGroupId`,
  `SourcePrefixListId`.
- Used for: the core discrimination of triage mode - whether ingress traffic
  on TCP 80 and 443 is accepted from the public internet. Each group bound to
  the instance is evaluated on its own (up to 10 groups; more is degraded with
  a `[WARN]`), then the per-group verdicts are merged per port: a group that
  is open to the public makes the port `allowed`, otherwise a Drop at the
  winning priority gives `blocked_by_drop_rule`, a narrower source gives
  `allowed_for_narrow_source_only`, and nothing allowing gives
  `no_inbound_allow_rule`. Within one group, rules are judged in ascending
  `Priority`, at equal priority a Drop beats an Accept, and traffic matching
  no rule is denied by default (ECS security-group semantics).
- Failure handling: a group whose rules could not be read produces a `[WARN]`
  line and an `errors[]` entry; its port results are simply absent rather than
  assumed open. If no group could be inspected at all the mode verdict is
  `INSUFFICIENT_EVIDENCE`, never a clean bill of health.

## 5. vpc DescribeEipAddresses

- Version: 2016-04-28.
- Request parameters actually sent: `RegionId`, `PageSize` (50), `PageNumber`
  (a region-wide listing; no address or binding filter is sent).
- Consumed response fields (per EIP in `EipAddresses.EipAddress[]`):
  `AllocationId`, `IpAddress`, `Status`, `Bandwidth`, `InstanceId`,
  `InstanceType`, `InternetChargeType`.
- Used for: the public-reachability leg of triage mode. The report highlights
  the EIPs whose `InstanceId` is the target instance or whose `IpAddress` is
  among its public addresses, and flags any such EIP whose `Status` is not
  `InUse` - an unbound or non-InUse EIP carries no traffic regardless of
  security-group rules.
- Failure handling: degrades with a `[WARN]` and an `errors[]` entry; the
  report then shows no EIP rows, which is stated as "none returned", not as a
  fabricated binding state.

## Not covered by any contract in this skill (do not invent calls)

- ICP filing data (orders, filing numbers, subjects, service codes): no
  verified API exists for this tier. Conclusions about filing status must
  come from a customer-provided ICP Filing console screenshot.
- DNS resolution records: no DNS read API is in scope. The customer checks
  the apex `@` record in the Alibaba Cloud DNS console.
- Guest OS state (listeners, services, hosts file): out of the read-only
  boundary; customer self-check guidance only.
- Orders, refunds, renewals, extensions: commercial actions; routed to
  specialists per `references/icp-filing-guide__escalation-map.md`.

## Alignment

`related_apis.yaml` at the skill root declares exactly the five actions above
with their real `popVersion` values, matching `API_WHITELIST` and
`API_VERSIONS` in `scripts/areas/icp_filing_guide/_constants.py` (imported and enforced at runtime by
`assert_read_only()` in `scripts/areas/icp_filing_guide/_cli.py`) and `references/ram-policies.md`
one-to-one.
