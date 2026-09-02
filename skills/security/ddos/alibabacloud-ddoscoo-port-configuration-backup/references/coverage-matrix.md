# Configuration Coverage Matrix

| Scope | Portable fields | Read | Restore | Invariant |
|---|---|---|---|---|
| Port identity | Protocol, FrontendPort | `DescribeNetworkRules` | `CreatePort` / `DeletePort` | Only `IsAutoCreate=false` |
| Base access | BackendPort, complete RealServers, Remark | `DescribeNetworkRules` | `CreatePort` / `ModifyPort` / `ConfigLayer4Remark` | Rebuild for a backend-port change or clearing a remark |
| Health check | Complete HealthCheck or `{}` | `DescribeHealthCheckList` | `ModifyHealthCheckConfig` | `{}` is an explicit disabled state |
| Persistence and port attributes | PersistenceTimeout; complete NodataConn, Synproxy, Sla, Slimit, PayloadLen, and other returned fields | `DescribeNetworkRuleAttributes` | `ModifyNetworkRuleAttribute` | Exclude `Cc`; preserve exact TCP and UDP PayloadLen |
| Primary/secondary origin | BakMode, CurrentIndex, PriRealServers, SecRealServers | `DescribeLayer4RulePolicy` | `ConfigLayer4RuleBakMode` / `ConfigLayer4RulePolicy` | Forwarding mode is fixed round-robin; query one port at a time |
| Application-layer enhancement | ProxyEnable, complete UsTimeout | `DescribeLayer4Rules` + `DescribePortProxyEnable` | `ConfigLayer4Rule` | Enhanced TCP; `0/0` is a real initial state and may require rebuild; poll up to 90 seconds |
| Payload | ModuleEnable, complete manual-rule semantics, temporary-block TTL | `DescribePortProxyEnable` + `DescribePortPayloadRuleList` | `ConfigPortPayloadRule` / `DeletePortPayloadRule` / `ConfigPortPayloadModuleEnable` | Preserve dormant rules while disabled; never modify automatic rules; stop on manual regex |
| L4 whitelist | Complete normalized list or `[]` | `DescribeL4ProxyWhiteList` | `ConfigL4ProxyWhiteList` / `DeleteL4ProxyWhiteList` | Whole-list desired state; enhanced TCP IPv4 |
| Advanced defense | Switch, Template | `DescribeLayer4SwitchAndDefense` | `ConfigLayer4SwitchAndDefense` | TCP IPv4; Mode is derived |
| Non-website AI | Switch, Mode | `DescribePortAutoCcStatus` | `ModifyPortAutoCcStatus` | Shared by the instance IP object and all non-website ports |

Explicitly exclude website-derived automatic rules, `Cc.Sblack`, regional
blocking, scenario-specific protection, Protection for Infrastructure, website
protection, instance specifications and usage, and runtime traffic,
connections, attacks, blackholes, and logs.

Omit an optional field only when the capability is inapplicable. Stop the
affected port on a failed read, denied permission, missing field, or
non-restorable value; never replace an unknown state with an empty value.
