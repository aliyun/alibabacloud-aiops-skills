# Import Workflow

`validate one-port YAML -> user selects target instance -> read target state -> resolve shared AI conflict -> restore directly in dependency order -> complete readback`

## Operating principle

One YAML defines the desired state of one port. After the user specifies the
input, target instance, and requests import, complete the required validation
and execute directly. Do not ask again at each stage. Skip a write when the
current value already equals the YAML; otherwise perform the documented write
and immediately read the affected state.

Modify only the port access and security policy represented in the YAML.
`Cc.Sblack`, regional blocking, instance specifications, website
configuration, and independent configuration of other ports are outside the
import scope. A conflict in instance-level non-website AI is the only extra
user decision because it affects every non-website port on the target
instance.

A RequestId means only that the request was accepted. Success requires exact
final readback of the business fields.

## 1. Validate the input and select the target instance

Obtain:

1. Exact paths to one or more YAML files, each containing exactly one port.
2. The target DDoS Pro instance ID selected by the user for every file. A
   backup is not bound to its source instance; never reuse the source
   automatically.
3. The user's explicit request to execute the import.

Read the target instance details to discover usable EIPs. Use it directly when
there is only one. Ask the user to choose when there are multiple usable EIPs.
Do not write before both the instance ID and EIP are resolved.

~~~bash
aliyun ddoscoo describe-instance-details --instance-ids '<TARGET_INSTANCE_ID>' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun ddoscoo describe-instance-specs --instance-ids '<TARGET_INSTANCE_ID>' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun ddoscoo describe-instance-statistics --instance-ids '<TARGET_INSTANCE_ID>' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

For these three commands, `--instance-ids` takes the exact instance ID as one
scalar string despite its plural name. Never encode it as a JSON array. All
three reads must succeed before import continues; otherwise EIP, capability,
capacity, or usage is incomplete and no cloud write may start. If a failed
call used the wrong array form, correct the parameter and rerun every failed
read.

Validate the YAML:

- the top level contains only `port`, `access_policy`, and `security_policy`;
- `port.protocol` is `tcp|udp` and both ports are in `1..65535`;
- the access policy contains the backend port, complete origin list, remark,
  health check, session persistence, and complete primary/secondary policy;
- `port_attributes` contains neither `Cc` nor `PersistenceTimeout`, and
  `PayloadLen.Min/Max` is present;
- optional application-layer protection contains only `ProxyEnable` and the
  complete `UsTimeout`;
- Payload rules contain no source RuleId and only writable manual semantics; a
  temporary block includes `ComputeRules.Ratelimit.Config.Ttl`, and a manual
  regex rule is rejected;
- advanced defense contains only `Switch` and `Template`;
- `non_website_ai` contains only `switch` and `mode`;
- the file contains no source instance, EIP, region, profile, specifications,
  usage, RequestId, or credential material.

Use target `EipInfos[]` for capability validation. Application-layer
enhancement, Payload, and L4 whitelist require enhanced TCP; Payload also
requires Mainland China IPv4; advanced defense requires TCP IPv4. If the YAML
contains a dimension unsupported by the target, list the incompatibility and
stop that port before any write. Never ignore or downgrade it silently.

An omitted optional dimension means the source capability was inapplicable,
not that the desired value is empty. If the target supports that dimension,
read its current state for an existing port. Stop if the target already has an
enabled or nonempty configuration that the backup cannot express. For a new
port, read these dimensions after creation; if a service default creates
nonempty configuration, do not claim exact equality.

## 2. Read the target and choose the base-rule branch

Paginate all rules for the target protocol to the server-reported total and
match exactly by `(protocol, frontend_port)`:

~~~bash
aliyun ddoscoo describe-network-rules \
  --instance-id '<TARGET_INSTANCE_ID>' --forward-protocol '<PROTOCOL>' \
  --page-number 1 --page-size 50 \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Use this protocol-filtered, fully paginated base-rule read for branch selection,
base-rule readback, the fresh ownership proof before deletion, and the absence
proof after deletion. If any required page fails or is incomplete, ownership
and port availability are unknown: stop before the next cloud write. Do not
substitute health-check, port-attribute, policy, or duplicate-create results
for the base-rule read.

- No rule: create a manual port.
- `IsAutoCreate=true`: a website rule occupies the identity; stop the port.
- Missing or non-Boolean `IsAutoCreate`: ownership is unknown; stop the port.
- Manual rule: read every applicable dimension, then skip, modify, or rebuild.

Rebuild an existing manual port if any of the following is true:

1. Its backend port differs from the YAML. `modify-port` reliably replaces the
   origin list but not the backend port.
2. The YAML remark is empty and the target remark is nonempty.
   `config-layer4-remark` cannot submit an empty string.
3. Enhanced TCP requires `ProxyEnable=0 + UsTimeout=0/0` and the target is not
   already in that exact state. `0/0` is the real initial state of a new port
   and cannot be submitted through the timeout write.

Before deletion, freshly prove the target still has `IsAutoCreate=false`.
Rebuild removes attached port policies, so continue through the complete YAML
restore; never restore only the field that triggered rebuild.

## 3. Resolve instance-level non-website AI conflicts

Read and decide once per target instance:

~~~bash
aliyun ddoscoo describe-port-auto-cc-status \
  --instance-ids '<TARGET_INSTANCE_ID>' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

`Switch + Mode` applies to the instance IP object and all non-website ports:

- if YAML files mapped to one instance disagree, ask the user to select one
  final value for that instance before import;
- if the backup differs from the target, explain the scope and let the user
  keep the target value or adopt the specified value;
- without an explicit choice, do not change the instance and do not start
  writes for any selected port on it;
- the response may also contain `WebSwitch` and `WebMode`; discard those fields
  immediately and never compare, preserve, log, report, or modify them.

Complete this read and every required conflict decision before entering
section 4. No `create-port`, `modify-port`, `delete-port`, or other cloud write
may occur first, even when the selected port does not yet exist.

## 4. Restore one port in dependency order

Use this fixed order. Proxy or primary/secondary transitions may asynchronously
reset health checks and port attributes, so those two dimensions are written
only after every transition has converged.

`temporarily disable primary/secondary mode when required -> base rule or rebuild -> Proxy and child policies -> final Proxy -> primary/secondary origin -> health check and port attributes -> advanced defense -> complete readback`

### 4.1 Create, modify, or rebuild the base rule

If an existing manual rule has `BakMode=1` and either the base rule or
application-layer enhancement must change, first disable primary/secondary
mode and read back `BakMode=0`. A missing or soon-to-be-rebuilt rule does not
need this step.

~~~bash
aliyun ddoscoo config-layer4-rule-bak-mode --bak-mode 0 \
  --listeners '[{"InstanceId":"<TARGET_INSTANCE_ID>","Protocol":"<PROTOCOL>","FrontendPort":<FRONTEND_PORT>}]' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Create a missing or rebuilt rule with Proxy disabled:

~~~bash
aliyun ddoscoo create-port \
  --instance-id '<TARGET_INSTANCE_ID>' --frontend-protocol '<PROTOCOL>' \
  --frontend-port <FRONTEND_PORT> --backend-port <BACKEND_PORT> \
  --real-servers '<ORIGIN_1>' '<ORIGIN_2>' '<ORIGIN_N>' --proxy-enable 0 \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

When only the origin list differs on an existing manual rule, submit the
complete YAML list and retain its current backend port:

~~~bash
aliyun ddoscoo modify-port \
  --instance-id '<TARGET_INSTANCE_ID>' --frontend-protocol '<PROTOCOL>' \
  --frontend-port <FRONTEND_PORT> --backend-port <CURRENT_BACKEND_PORT> \
  --real-servers '<ORIGIN_1>' '<ORIGIN_2>' '<ORIGIN_N>' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

For a rebuild:

~~~bash
aliyun ddoscoo delete-port \
  --instance-id '<TARGET_INSTANCE_ID>' --frontend-protocol '<PROTOCOL>' \
  --frontend-port <FRONTEND_PORT> \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

# Read back and prove the exact identity is absent, then run create-port.
~~~

Write a nonempty YAML remark when it differs. An empty remark is achieved only
when the target is already empty or through the documented rebuild:

~~~bash
aliyun ddoscoo config-layer4-remark \
  --listeners '[{"InstanceId":"<TARGET_INSTANCE_ID>","Protocol":"<PROTOCOL>","FrontendPort":<FRONTEND_PORT>,"Remark":"<REMARK>"}]' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

After every command, read the base rule and compare the backend port, complete
origin set, and remark exactly.

### 4.2 Restore Proxy, origin timeout, Payload, and whitelist

This section applies only when the YAML contains
`application_layer_protection` for enhanced TCP. `ConfigLayer4Rule` is the
single Proxy and `UsTimeout` write. Submit both in the same request.

Use the latest complete listener read from the base rule:

~~~bash
aliyun ddoscoo config-layer4-rule --api-version 2017-12-28 \
  --listeners '[{"InstanceId":"<TARGET_INSTANCE_ID>","Protocol":"tcp","FrontendPort":<FRONTEND_PORT>,"BackendPort":<BACKEND_PORT>,"RealServers":["<ORIGIN_1>","<ORIGIN_N>"]}]' \
  --proxy-enable <0_OR_1> \
  --us-timeout ConnectTimeout=<CONNECT_TIMEOUT> RsTimeout=<RS_TIMEOUT> \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

After submission, run both reads every 5 seconds for up to 90 seconds. Continue
only when both report the expected `ProxyEnable` and `ProxyStatus`. A live
transition can exceed 30 seconds, so three fixed reads are insufficient.

~~~bash
aliyun ddoscoo describe-layer4-rules --api-version 2017-12-28 \
  --instance-id '<TARGET_INSTANCE_ID>' --offset 0 --page-size 50 \
  --forward-protocol tcp --frontend-port <FRONTEND_PORT> \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun --auto-plugin-install false ddoscoo DescribePortProxyEnable --force \
  --Listeners '[{"Eip":"<TARGET_EIP>","Protocol":"tcp","FrontendPort":<FRONTEND_PORT>}]' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Branch rules:

- If all application-layer fields and child policies already match, write
  nothing.
- If the YAML requires `ProxyEnable=0 + UsTimeout=0/0`, Payload must be
  disabled with no manual rules and the whitelist must be empty. If the target
  differs, rebuild under section 2. Never submit `0/0`.
- For every other state, first ensure Proxy and the YAML's nonzero
  `UsTimeout` converge at `1/on`. Skip the write if already exact; otherwise
  call `ConfigLayer4Rule` and wait. Restore Payload and whitelist next. If the
  YAML's final Proxy state is off, call `ConfigLayer4Rule` again with the same
  timeout and `ProxyEnable=0`, then wait for `0/off`.

After every Proxy convergence, reread the base rule and prove that the complete
origin set, backend port, and remark did not drift. Stop immediately on drift.

#### Payload

The Payload rule set and module state are independent desired values. Preserve
dormant rules even when the module is disabled. Operate only on manual rules;
leave automatic rules unchanged.

Use `Priority + RuleName` as the normalized key. Business content includes
`Action`, complete `Conditions`, and
`ComputeRules.Ratelimit.Config.Ttl` for a temporary block. Ignore server
RuleId, Owner, Enable, ExpireTime, Vip, Protocol, and Port in comparison.

- Exact match: skip.
- Target manual rule absent from the YAML: delete its current RuleId.
- YAML rule absent from the target: create with `RuleId=""`.
- Same key with different content: delete the target current manual RuleId,
  then create with an empty RuleId.
- Reject manual regex. A permanent block has no TTL; a temporary block has TTL
  in `300..600`.

~~~bash
aliyun --auto-plugin-install false ddoscoo ConfigPortPayloadRule --force \
  --Vip '<TARGET_EIP>' --Protocol tcp --Port <FRONTEND_PORT> \
  --Rules '<ONE_MANUAL_RULE_JSON_ARRAY>' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun --auto-plugin-install false ddoscoo DeletePortPayloadRule --force \
  --Vip '<TARGET_EIP>' --Protocol tcp --Port <FRONTEND_PORT> \
  --Rules '["<TARGET_MANUAL_RULE_ID>"]' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun --auto-plugin-install false ddoscoo DescribePortPayloadRuleList --force \
  --Vip '<TARGET_EIP>' --Protocol tcp --Port <FRONTEND_PORT> \
  --PageNumber 1 --PageSize 100 \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Read the complete rule set after every create or delete. After rule
convergence, write the final module state:

~~~bash
aliyun --auto-plugin-install false ddoscoo ConfigPortPayloadModuleEnable --force \
  --Vip '<TARGET_EIP>' --Protocol tcp --Port <FRONTEND_PORT> --Enable <0_OR_1> \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

The final total is at most 10 rules including automatic rules, and every rule
has at most 10 conditions.

#### L4 whitelist

Replace the whole nonempty list or explicitly clear an empty list. Use exactly
one write:

~~~bash
aliyun --auto-plugin-install false ddoscoo ConfigL4ProxyWhiteList --force \
  --Eip '<TARGET_EIP>' --Protocol tcp --Port <FRONTEND_PORT> \
  --Whitelist '<WHITELIST_JSON_ARRAY>' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun --auto-plugin-install false ddoscoo DeleteL4ProxyWhiteList --force \
  --Eip '<TARGET_EIP>' --Protocol tcp --Port <FRONTEND_PORT> \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun --auto-plugin-install false ddoscoo DescribeL4ProxyWhiteList --force \
  --Eip '<TARGET_EIP>' --Protocol tcp --Port <FRONTEND_PORT> \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Compare the server-normalized values; for example, an input `/32` may read
back as one IP.

### 4.3 Restore primary/secondary origin

Restore the YAML's final primary/secondary state only after Proxy and its child
policies have finished.

For `BakMode=1`, enable and read back first, then submit the complete primary
group, secondary group, and current group:

~~~bash
aliyun ddoscoo config-layer4-rule-bak-mode --bak-mode 1 \
  --listeners '[{"InstanceId":"<TARGET_INSTANCE_ID>","Protocol":"<PROTOCOL>","FrontendPort":<FRONTEND_PORT>}]' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}

aliyun ddoscoo config-layer4-rule-policy \
  --listeners '[{"InstanceId":"<TARGET_INSTANCE_ID>","Protocol":"<PROTOCOL>","FrontendPort":<FRONTEND_PORT>,"BackendPort":<BACKEND_PORT>,"PriRealServers":[{"RealServer":"<PRIMARY_1>"}],"SecRealServers":[{"RealServer":"<SECONDARY_1>"}],"CurrentRsIndex":<CURRENT_INDEX>}]' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

For `BakMode=0`, keep the base rule's ordinary `real_servers` equal to the
YAML, then write and read back only BakMode. Do not call the policy write.
Every policy read contains one port identity.

~~~bash
aliyun ddoscoo describe-layer4-rule-policy \
  --listeners '[{"InstanceId":"<TARGET_INSTANCE_ID>","Protocol":"<PROTOCOL>","FrontendPort":<FRONTEND_PORT>}]' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

### 4.4 Restore health check and port attributes last

Execute this section only after Proxy and primary/secondary state have
converged, so asynchronous transitions cannot overwrite the final values.

~~~bash
aliyun ddoscoo modify-health-check-config \
  --instance-id '<TARGET_INSTANCE_ID>' --forward-protocol '<PROTOCOL>' \
  --frontend-port <FRONTEND_PORT> --health-check '<HEALTH_CHECK_JSON>' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

`{}` explicitly clears the health check. The port-attribute write replaces
the complete object. First read the target's full `Config`, preserve its full
`Cc`, replace `PersistenceTimeout` and the other corresponding fields with
the YAML values, then submit the complete object once. If the target has an
unknown sibling field not represented by the YAML and not `Cc`, stop and do
not guess.

~~~bash
aliyun ddoscoo modify-network-rule-attribute \
  --instance-id '<TARGET_INSTANCE_ID>' --forward-protocol '<PROTOCOL>' \
  --frontend-port <FRONTEND_PORT> --config '<COMPLETE_CONFIG_JSON>' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Read back and prove every YAML attribute equal, exact `PayloadLen.Min/Max`,
and the original target `Cc` unchanged. The service may normalize inactive
values; the actual readback remains authoritative, and any mismatch stops the
port.

### 4.5 Restore advanced defense

Write advanced defense after final port attributes so Synproxy is ready when
required. Write and compare only `Switch + Template`. Ignore an optional
derived `Mode`.

~~~bash
aliyun --auto-plugin-install false ddoscoo ConfigLayer4SwitchAndDefense --force \
  --Listeners '[{"eip":"<TARGET_EIP>","frontend_port":<FRONTEND_PORT>,"protocol":"tcp"}]' \
  --Config '{"switch":"<on_or_off>","template":"<weak_default_or_hard>"}' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

## 5. Write the shared instance AI state

Write at most once per instance, only when section 3 selected a new value and
every selected port on that instance restored successfully:

~~~bash
aliyun ddoscoo modify-port-auto-cc-status \
  --instance-id '<TARGET_INSTANCE_ID>' \
  --switch '<on_or_off>' --biz-mode '<normal_loose_or_strict>' \
  --profile '<PROFILE>' --region '<REGION>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Read back and compare only `Switch + Mode`. Discard `WebSwitch/WebMode` even
when the response contains them. If any selected port fails, do not change
shared AI.

## 6. Final verification and result

Read every applicable dimension again for each port and compare:

- base rule: backend port, complete origin list, remark, and manual ownership;
- health check and complete port attributes;
- primary/secondary mode, active group, and both origin groups;
- Proxy, ProxyStatus, and complete UsTimeout;
- Payload module, manual-rule semantics, and temporary-block TTL;
- complete whitelist;
- advanced-defense `Switch + Template`;
- shared AI `Switch + Mode` once per target instance, whether the value was
  retained or changed.

The section 3 pre-check is not final readback evidence. After all selected port
writes finish, freshly call `describe-port-auto-cc-status` and compare only
`Switch + Mode`. If section 5 changed shared AI, its post-write read satisfies
this requirement; otherwise perform a new read without issuing an AI write.
Never compare or preserve `WebSwitch/WebMode`.

Sort IP sets whose order has no semantic meaning. Ignore Payload RuleId and
advanced-defense Mode. A failed, missing, or unconverged field prevents a
complete-success result for that port. Do not automatically roll back writes
that already succeeded. Report the failed field, expected value, actual value,
and stopping step. Report success only when every applicable field matches.
