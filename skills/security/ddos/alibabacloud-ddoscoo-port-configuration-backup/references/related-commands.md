# Verified Aliyun CLI Commands

Every cloud command must include:

~~~
--profile <PROFILE> --region <REGION> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/<SESSION_ID>
~~~

Use the command names, case, API version, and JSON parameter shape shown here.
PascalCase Actions use:

~~~
aliyun --auto-plugin-install false ddoscoo <Action> --force <PARAMETERS>
~~~

## Read commands

| Configuration | Command |
|---|---|
| Instance | `describe-instances --instance-ids <ID> --page-number <N> --page-size <N>` |
| EIP and capability | `describe-instance-details --instance-ids <ID>` |
| Specifications and usage | `describe-instance-specs --instance-ids <ID>`; `describe-instance-statistics --instance-ids <ID>` |
| Base port rule | `describe-network-rules --instance-id <ID> --forward-protocol <P> --page-number <N> --page-size <N>` |
| Health check | `describe-health-check-list --network-rules '<ONE_PORT_JSON_ARRAY>'` |
| Complete port attributes | `describe-network-rule-attributes --network-rules '<ONE_PORT_JSON_ARRAY>'` |
| Primary/secondary policy | `describe-layer4-rule-policy --listeners '<ONE_PORT_JSON_ARRAY>'`; one port per request |
| Proxy and origin timeout | `describe-layer4-rules --api-version 2017-12-28 --instance-id <ID> --offset <N> --page-size <N> --forward-protocol <P> --frontend-port <PORT>` |
| Proxy and Payload-module cross-check | `DescribePortProxyEnable --Listeners '[{"Eip":"<EIP>","Protocol":"tcp","FrontendPort":<PORT>}]'` |
| Payload rules | `DescribePortPayloadRuleList --Vip <EIP> --Protocol tcp --Port <PORT> --PageNumber 1 --PageSize 100` |
| L4 whitelist | `DescribeL4ProxyWhiteList --Eip <EIP> --Protocol tcp --Port <PORT>` |
| Advanced defense | `DescribeLayer4SwitchAndDefense --Listeners '[{"eip":"<EIP>","frontend_port":<PORT>,"protocol":"tcp"}]'` |
| Non-website AI | `describe-port-auto-cc-status --instance-ids <ID>` |

## Write commands

| Configuration | Command | Constraint |
|---|---|---|
| Create port | `create-port --instance-id <ID> --frontend-protocol <P> --frontend-port <PORT> --backend-port <PORT> --real-servers <IP...> --proxy-enable 0` | May begin receiving traffic immediately |
| Replace origins | `modify-port --instance-id <ID> --frontend-protocol <P> --frontend-port <PORT> --backend-port <CURRENT> --real-servers <IP...>` | Submit the complete list; rebuild for a backend-port change |
| Delete port | `delete-port --instance-id <ID> --frontend-protocol <P> --frontend-port <PORT>` | Freshly prove `IsAutoCreate=false` |
| Remark | `config-layer4-remark --listeners '<ONE_PORT_REMARK_JSON_ARRAY>'` | Cannot submit an empty remark; rebuild to clear |
| Health check | `modify-health-check-config --instance-id <ID> --forward-protocol <P> --frontend-port <PORT> --health-check '<JSON_OBJECT>'` | `{}` explicitly clears |
| Port attributes | `modify-network-rule-attribute --instance-id <ID> --forward-protocol <P> --frontend-port <PORT> --config '<COMPLETE_CONFIG>'` | Full-object replacement; preserve target `Cc` |
| Proxy and origin timeout | `config-layer4-rule --api-version 2017-12-28 --listeners '<COMPLETE_LISTENER>' --proxy-enable <0_OR_1> --us-timeout ConnectTimeout=<N> RsTimeout=<N>` | Unified write; do not submit `0/0`; rebuild when required |
| Primary/secondary switch | `config-layer4-rule-bak-mode --bak-mode <0_OR_1> --listeners '<ONE_PORT_JSON_ARRAY>'` | Temporarily disable before Proxy changes and restore last |
| Primary/secondary policy | `config-layer4-rule-policy --listeners '<ONE_COMPLETE_POLICY_JSON_ARRAY>'` | After `BakMode=1`, submit both full groups and the active group |
| Payload rule | `ConfigPortPayloadRule --Vip <EIP> --Protocol tcp --Port <PORT> --Rules '<ONE_RULE_JSON_ARRAY>'` | Empty RuleId for create; preserve temporary-block TTL |
| Delete Payload rule | `DeletePortPayloadRule --Vip <EIP> --Protocol tcp --Port <PORT> --Rules '["<TARGET_RULE_ID>"]'` | Delete only a current target manual rule |
| Payload module | `ConfigPortPayloadModuleEnable --Vip <EIP> --Protocol tcp --Port <PORT> --Enable <0_OR_1>` | Write after rule convergence |
| Nonempty L4 whitelist | `ConfigL4ProxyWhiteList --Eip <EIP> --Protocol tcp --Port <PORT> --Whitelist '<FULL_JSON_ARRAY>'` | Whole-list replacement |
| Clear L4 whitelist | `DeleteL4ProxyWhiteList --Eip <EIP> --Protocol tcp --Port <PORT>` | Read back as a normalized empty list |
| Advanced defense | `ConfigLayer4SwitchAndDefense --Listeners '<ONE_PORT_JSON_ARRAY>' --Config '{"switch":"<on_or_off>","template":"<weak_default_or_hard>"}'` | Write only Switch and Template |
| Non-website AI | `modify-port-auto-cc-status --instance-id <ID> --biz-mode <MODE> --switch <on_or_off>` | Instance-shared; at most once per target instance |

The complete Proxy, Payload, and whitelist order is defined only in
[`import-workflow.md`](import-workflow.md). Do not infer execution order from
this index.
