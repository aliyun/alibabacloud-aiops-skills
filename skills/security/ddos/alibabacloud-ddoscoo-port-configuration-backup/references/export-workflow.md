# Export Workflow

`select port scope -> identify manual rules and capabilities -> read complete configuration -> emit one YAML per port -> read everything again -> deliver`

Use the profile, region, resource-group scope, session ID, and export scope
already confirmed by `SKILL.md`. Do not repeat the common CLI, authentication,
or permission checks here.

## 1. Select ports and output location

Support a single port, multiple ports, an instance, or an account scope.
Regardless of scope, emit a separate YAML for every
`(protocol, frontend_port)`. Never combine multiple ports in one file.

If the user does not specify a location, use `./ddoscoo-port-backups/` under
the current working directory. Otherwise use the requested directory. The
default filename is `<protocol>-<frontend_port>.yaml`.

If the user provides only a port number, perform one limited
`describe-network-rules` discovery:

- match only manual rules with `IsAutoCreate=false`;
- if both TCP and UDP exist, ask whether to export one or both;
- the exact identity is `(protocol, frontend_port)`, not a port number alone.

## 2. Identify the instance, EIP, capabilities, and manual rule

Discover instances from the user-selected IP, instance, or account scope and
paginate to the server-reported total. Omit `--resource-group-id` for the
default resource group. For another group, use the exact confirmed ID.

~~~bash
aliyun ddoscoo describe-instances --ip '<SOURCE_IP>' \
  --page-number 1 --page-size 50 \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun ddoscoo describe-instance-details --instance-ids '<INSTANCE_ID>' \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun ddoscoo describe-network-rules --instance-id '<INSTANCE_ID>' \
  --page-number 1 --page-size 50 \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Accept only a base rule with `IsAutoCreate=false`. Exclude
website-generated automatic rules before any per-port detail read. If
`IsAutoCreate` is missing or is not a Boolean, stop that port.

Read the current EIP, `FunctionVersion`, IP mode, and IP version from
`EipInfos[]`. Use them only for capability decisions; never write them to the
YAML. `FunctionVersion=enhance` identifies enhanced capabilities:
application-layer protection enhancement, session-feature filtering, and the
L4 whitelist depend on it. If a capability field is missing or unrecognized,
stop the affected port. Never convert an unread configuration to disabled or
empty.

## 3. Read one port's complete business configuration

Associate every response by `instance + protocol + frontend port`, never by
array position.

### 3.1 Access rule, health check, port attributes, and origin policy

Use the current `describe-network-rules` row from section 2 for the base rule.
Save the backend port, complete origin list, and remark. Origin forwarding mode
is fixed round-robin and has no YAML field.

~~~bash
aliyun ddoscoo describe-health-check-list \
  --network-rules '[{"InstanceId":"<INSTANCE_ID>","Protocol":"<PROTOCOL>","FrontendPort":<FRONTEND_PORT>}]' \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun ddoscoo describe-network-rule-attributes \
  --network-rules '[{"InstanceId":"<INSTANCE_ID>","Protocol":"<PROTOCOL>","FrontendPort":<FRONTEND_PORT>}]' \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun ddoscoo describe-layer4-rule-policy \
  --listeners '[{"InstanceId":"<INSTANCE_ID>","Protocol":"<PROTOCOL>","FrontendPort":<FRONTEND_PORT>}]' \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Query `describe-layer4-rule-policy` for one port at a time. Save `BakMode`,
`CurrentIndex`, `PriRealServers[].RealServer`, and
`SecRealServers[].RealServer`. The base rule is authoritative for the backend
port; do not use a policy response that may report `BackendPort=0`.

Split the complete `Config` response as follows:

- save `PersistenceTimeout` under
  `access_policy.session_persistence`;
- save every field except `Cc` and `PersistenceTimeout` under
  `security_policy.port_attributes`.

`Cc.Sblack` is not a port-object configuration and must not enter the backup.
`PayloadLen.Min/Max` is real configuration for both TCP and UDP; preserve the
returned values exactly without adding defaults or truncating them.

An empty health-check object `{}` is the explicit disabled state and must be
saved. A missing field is not `{}`.

### 3.2 Application-layer protection enhancement and origin timeout

Read only for enhanced TCP:

~~~bash
aliyun ddoscoo describe-layer4-rules --api-version 2017-12-28 \
  --instance-id '<INSTANCE_ID>' --offset 0 --page-size 50 \
  --forward-protocol tcp --frontend-port <FRONTEND_PORT> \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Select the unique exact-port listener and save `ProxyEnable` and the complete
`UsTimeout`. With Proxy disabled, enhanced TCP may return the real state
`0/0` or a nonzero state such as `3/600`. Preserve the exact values; do not
merge either into a default.

If one response is incomplete, the next `Offset` equals the number of records
already read, not a page number. Add the number of listeners returned by each
response until the deduplicated listener count equals `Total`.

### 3.3 Payload, L4 whitelist, and advanced defense

Run each read only when its capability applies:

~~~bash
aliyun --auto-plugin-install false ddoscoo DescribePortProxyEnable --force \
  --Listeners '[{"Eip":"<SOURCE_EIP>","Protocol":"tcp","FrontendPort":<FRONTEND_PORT>}]' \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun --auto-plugin-install false ddoscoo DescribePortPayloadRuleList --force \
  --Vip '<SOURCE_EIP>' --Protocol tcp --Port <FRONTEND_PORT> \
  --PageNumber 1 --PageSize 100 \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun --auto-plugin-install false ddoscoo DescribeL4ProxyWhiteList --force \
  --Eip '<SOURCE_EIP>' --Protocol tcp --Port <FRONTEND_PORT> \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun --auto-plugin-install false ddoscoo DescribeLayer4SwitchAndDefense --force \
  --Listeners '[{"eip":"<SOURCE_EIP>","frontend_port":<FRONTEND_PORT>,"protocol":"tcp"}]' \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Capability gates:

- Payload: Mainland China, enhanced, TCP, IPv4;
- L4 whitelist: enhanced, TCP, IPv4;
- advanced defense: TCP, IPv4;
- do not read those three dimensions for UDP; do not read Payload or L4
  whitelist for a default-function EIP.

Read `PayloadRuleEnable` as the Payload module switch. Paginate the complete
rule list, then:

1. Back up only `Owner=manual`. Do not include automatic rules. Stop if Owner
   is missing or unknown.
2. Save `Priority`, `RuleName`, `Action`, and complete `Conditions` for every
   rule.
3. For a temporary block, also save
   `ComputeRules.Ratelimit.Config.Ttl`. Do not save empty `ComputeRules` for
   permanent-block or observe rules.
4. Do not save `RuleId`, `Owner`, `Enable`, `ExpireTime`, Vip, Protocol, or
   Port; those values are source identity, derived, or runtime fields.
5. If a manual rule has `Pattern=regex`, stop the port export. The write Action
   rejects regex, so the workflow must not generate a backup that cannot be
   restored exactly.

When a successful whitelist read omits `Data`, normalize it to an explicit
empty list `[]`. Save nonempty values after server normalization; for example,
`/32` may read back as one IP.

For advanced defense, save only `Switch` and `Template`. `Mode` may appear,
disappear, or be derived from the template and is not independently writable.

### 3.4 Instance-level non-website AI

Read once per instance:

~~~bash
aliyun ddoscoo describe-port-auto-cc-status \
  --instance-ids '<INSTANCE_ID>' \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

The product has IP and domain objects but no independent port object.
`Switch` and `Mode` apply to the instance IP object and therefore to all
non-website ports on that instance. Every per-port YAML from one instance must
record the same `non_website_ai.switch/mode`. Do not save website
`WebSwitch` or `WebMode`.

## 4. Build the one-port YAML

The top level may contain only:

- `port` with `protocol` and `frontend_port`;
- `access_policy` with `backend_port`, `real_servers`, `remark`, complete
  `health_check`, `session_persistence.PersistenceTimeout`, and
  `origin_policy.BakMode/CurrentIndex/PriRealServers/SecRealServers`;
- `security_policy` with `port_attributes` and, when applicable,
  `application_layer_protection`, `payload`, `l4_proxy_whitelist`,
  `advanced_defense`, plus `non_website_ai`.

Omit optional dimensions whose capability is inapplicable. Preserve a
successfully read empty object or empty list. Never include the source instance
ID, EIP, region, resource group, profile, FunctionVersion, specifications,
usage, RequestId, runtime state, or credential material.

If enhanced TCP has `ProxyEnable=0` and `UsTimeout=0/0`, Payload must also be
disabled with no manual rules and the whitelist must be empty. Otherwise exact
restore cannot preserve `0/0`; stop the export and report the conflict.

## 5. Read again and deliver

Repeat every applicable read for the port and compare the normalized business
fields:

- unordered IP lists may be sorted; compare Payload rules by
  `Priority + RuleName`;
- include temporary-block TTL in Payload comparison but ignore generated
  RuleId;
- compare advanced defense only by `Switch + Template`;
- stop delivery on any changed, failed, or missing field.

Before delivery, validate YAML syntax, one-port-per-file structure, field
completeness, and absence of sensitive data. Set file mode to `0600` and
calculate SHA-256. If a target file already exists, never overwrite it
silently; ask for another path or explicit overwrite approval.
