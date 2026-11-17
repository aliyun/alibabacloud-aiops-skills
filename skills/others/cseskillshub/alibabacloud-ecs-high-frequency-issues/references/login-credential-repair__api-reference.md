# API reference for the automated surface

Every action below is declared in `related_apis.yaml`, listed in
[ram-policies.md](ram-policies.md), and permitted by the runtime whitelist in
`scripts/areas/login_credential_repair/_cli.py` (`assert_whitelisted`). An action outside this page cannot be
dispatched by the scripts even if it is requested.

| Product | API version | Actions actually called |
| --- | --- | --- |
| `ecs` | `2014-05-26` | `DescribeInstances`, `DescribeInstanceAttribute`, `DescribeKeyPairs`, `DescribeCloudAssistantStatus`, `DescribeInvocations` |
| `sts` | `2015-04-01` | `GetCallerIdentity` |

CLI shape: the transport builds an argument list, never a shell string.
RPC-style products pass the PascalCase action name as one argument (for
example the `ecs` product with `DescribeInstances`); the plugin-style `sts`
product uses its lowercase hyphenated command (`aliyun sts get-caller-identity`). Region scoping is passed
as `--region` in addition to any `RegionId` parameter the action defines. Every
call carries `--user-agent` and an explicit per-call timeout.

Field names in the "fields consumed" columns marked *(candidate)* are read
tolerantly: if the response does not contain them, the report prints `not
returned`. Nothing is defaulted, inferred or filled in.

## 1. `sts:GetCallerIdentity` (`scripts/areas/login_credential_repair/sts_token.py`)

- **Parameters:** none.
- **Fields consumed:** `AccountId` *(candidate alternatives: `AccountUid`,
  `Uid`)*, `Arn` *(alternatives: `UserId`, `PrincipalId`)*, `IdentityType`
  *(candidate)*. The account is additionally parsed out of an
  `acs:ram::<account>:...` ARN when no explicit account field is present.
- **Purpose:** prove the local default credential chain works, and derive the
  account traceability label printed in the report header. The label keeps only
  the last four digits.
- **Failure handling:** a credential-chain failure is classified separately
  from a permission failure and yields the guidance to refresh the local CLI
  configuration. The scripts never accept, read, print or pass key material.

## 2. `ecs:DescribeInstances` (`login_credential_diagnose.py`)

- **Parameters sent:** `RegionId` (required), `InstanceIds` (JSON array string,
  only when an instance id was supplied), then `PageSize` / `PageNumber` from
  the pager.
- **Response path:** `Instances.Instance[]`; total from `TotalCount`.
- **Fields consumed:** `InstanceId`, `InstanceName`, `Status`, `OSType`,
  `OSName`, `InstanceType`, `ZoneId`, `KeyPairName`,
  `PublicIpAddress.IpAddress[]`, `EipAddress.IpAddress`,
  `InnerIpAddress.IpAddress[]`, `VpcAttributes.PrivateIpAddress.IpAddress[]`.
- **What it decides:** OS family (which branch vocabulary and which guided
  command type applies), whether the instance is `Running` or `Stopped`, and
  whether a public address or EIP exists at all - the fact that settles the
  "dialed the private address" branch without any in-guest access.
- **Note:** `OSType` is lower-cased and matched against `windows` / `linux`;
  anything else is reported as `unknown`, never guessed.

## 3. `ecs:DescribeInstanceAttribute`

- **Parameters sent:** `InstanceId` (the single verified required parameter).
- **Fields consumed:** `Status`, `InstanceNetworkType`, `OSName`,
  `InstanceType`, `PublicIpAddress`, `InnerIpAddress`.
- **Purpose:** a second, single-instance authoritative read of state and
  addresses, so a listing quirk or a stale page does not drive the conclusion.

## 4. `ecs:DescribeKeyPairs`

- **Parameters sent:** `RegionId`, `KeyPairName` (exact name), plus paging with
  a two-page ceiling per name.
- **Response path:** `KeyPairs.KeyPair[]`; `KeyPairName` compared.
- **Names queried:** the binding reported by `DescribeInstances`, plus any name
  the customer supplied via `--key-pair-name`.
- **What it decides:** whether "the key pair has been removed" is a fact
  (`missing`) or a red herring (`present`). Both outcomes are reported; the
  absence of a result is stated as such rather than described as an error.

## 5. `ecs:DescribeCloudAssistantStatus`

- **Parameters sent:** `RegionId`, `InstanceId.1` (the repeat-parameter form).
- **Response path:** `CloudAssistantStatusSet.CloudAssistantStatus[]`.
- **Fields consumed:** `CloudAssistantStatus` (string `"true"` / `"false"`,
  mapped to online / offline / unknown), `CloudAssistantVersion` *(candidate)*,
  `LastHeartbeatTime` then `LastInvocationTime` *(candidates)*,
  `SupportInstanceConnect` then `AgentSupportMonitor` *(candidates)*.
- **Why it is the most valuable read in this skill:** the console online
  password reset and the passwordless Workbench route both depend on this
  agent. In the evidence for this tier, "the agent must be broken" was asserted
  repeatedly and never checked. This call makes it a field, and its result is
  also the gate that decides whether guiding a customer into a Cloud Assistant
  command page is worth their time at all.
- **When it is unknown** (call failed, no record returned, or no instance id in
  scope), the report says online-reset feasibility is unverified and the run
  cannot end as `STATUS: OK`.

## 6. `ecs:DescribeInvocations`

- **Parameters sent:** `RegionId`, `InstanceId`, paging with a small page size
  and a two-page ceiling; at most 40 records are rendered.
- **Response path:** `Invocations.Invocation[]`.
- **Fields consumed:** `CommandName` *(alternative `Name`)*, `CommandType`
  *(alternative `Type`)*, `InvocationStatus` *(alternative `Status`)*,
  `CreateTime` *(alternative `CreationTime`)*.
- **`IncludeOutput` is deliberately not set.** The command output of an
  invocation can contain whatever the command printed, including secrets. This
  skill needs the *record* - what ran, when, and whether it reached the
  instance - not the payload, so it does not request the body.
- **What it decides:** the difference between "the console task shows success"
  and "the guest was ever told". That is the whole LC3 hidden-failure branch.
- **Caveat to relay with any conclusion drawn from it:** this action returns
  invocation records, i.e. history, not a live liveness probe. Pair it with
  `DescribeCloudAssistantStatus` rather than reading it as "the agent is fine
  right now".

## 7. Command types in the guided console flows (not dispatched here)

When the playbooks guide a customer through the Cloud Assistant command page,
the command type must match the guest OS:

| Guest OS | Command style the lines are written for | Console type |
| --- | --- | --- |
| Linux | shell lines | the shell / `RunShellScript` style |
| Windows | command-prompt lines such as `net accounts` | **Bat** - not Shell |

The Windows row is not pedantry: leaving the type on Shell produced "the Run
button is greyed out" and a wasted support round trip in this tier's evidence,
and the type is decided automatically when the OS family comes from
`DescribeInstances`. This mapping documents the guidance; it is not used to
build a call, because the skill sends no command.

## 8. Not declared, not called, and not to be added casually

| Capability | Status here | Why |
| --- | --- | --- |
| `ModifyInstanceAttribute` with the `Password` field | Never called | Delegated password reset needs an explicit grant decision first; the customer uses the console wizard |
| `CreateSnapshot` | Never called | The snapshot-first rule is enforced as guidance; the call shape (per-disk versus all disks, name, consistency group) was not confirmed by the evidence, so no parameters are invented |
| `RunCommand` | Never called | The in-guest whitelist was not extended to the credential area; readings are customer-executed |
| `StartInstance` / `StopInstance` / `RebootInstance` | Never called | Restarts are a business-window decision for the customer |
| Security-group reads and writes | Never called, no contract in the evidence | The skill gives console guidance only, and says it cannot see the rules |
| Any console session link generator | Never called, no contract in the evidence | Console navigation is printed as text |
| Disk listing and monitoring reads | Never called | Disk-full and resource-exhaustion cases are identified and handed off, so the permissions are not requested |

## 9. Pending verification before this surface grows

1. **Asynchronous behaviour of the command channel** (polling interval, maximum
   wait, per-command output length ceiling, what to tell the customer on a
   timeout). Unresolved, so the scripts carry no magic constants for it: a
   guided run that does not succeed degrades immediately instead of polling.
2. **Error-code table** for the reset and command actions. No code table exists
   in the evidence for this tier, so no code is referenced anywhere in the
   package. Routing uses the verbatim customer-visible wording plus API fields.
3. **`CreateSnapshot` parameter shape** if snapshot creation is ever automated.
4. **Security-group and session-link actions** if rule inspection is ever
   authorized; both need a verified contract before appearing in
   `related_apis.yaml`.

Any of those becoming real requires updating `related_apis.yaml`,
[ram-policies.md](ram-policies.md), `scripts/areas/login_credential_repair/_constants.py`
(`CLOUD_INSPECTION_WHITELIST`) and this page together - the four must never
disagree.
