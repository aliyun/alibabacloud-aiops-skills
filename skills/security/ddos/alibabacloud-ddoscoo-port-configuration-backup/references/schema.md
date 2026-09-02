# One-Port YAML Schema

Each file describes the portable desired state of exactly one manual port. The
top level is fixed:

~~~yaml
port:
  protocol: tcp
  frontend_port: 4433
access_policy:
  backend_port: 8443
  real_servers:
    - 192.0.2.10
  remark: example
  health_check: {}
  session_persistence:
    PersistenceTimeout: 0
  origin_policy:
    BakMode: 0
    CurrentIndex: 1
    PriRealServers: []
    SecRealServers: []
security_policy:
  port_attributes:
    NodataConn: "off"
    PayloadLen:
      Min: 0
      Max: 6000
    Sla:
      Cps: 100000
      CpsEnable: 1
      Maxconn: 2000000
      MaxconnEnable: 1
    Slimit:
      Bps: 0
      Pps: 0
      Cps: 0
      CpsEnable: 0
      CpsMode: 1
      Maxconn: 0
      MaxconnEnable: 0
    Synproxy: "on"
  application_layer_protection:
    ProxyEnable: 1
    UsTimeout:
      ConnectTimeout: 3
      RsTimeout: 600
  payload:
    ModuleEnable: 1
    Rules:
      - Priority: 11
        RuleName: allow_protocol
        Action: observe
        Conditions:
          - Encode: str
            Offset:
              Start: 0
              End: 100
            Pattern: contain
            Content: HELLO
      - Priority: 31
        RuleName: temporary_block
        Action: block
        Conditions:
          - Encode: hex
            Offset:
              Start: 0
              End: 100
            Pattern: contain
            Content: DEADBEEF
        ComputeRules:
          Ratelimit:
            Config:
              Ttl: 300
  l4_proxy_whitelist:
    - 198.51.100.0/24
  advanced_defense:
    Switch: "on"
    Template: default
  non_website_ai:
    switch: "on"
    mode: normal
~~~

## Required fields

- `port.protocol` is `tcp|udp` and `frontend_port` is an integer from 1
  through 65535.
- All six `access_policy` children shown above are required. Use `""` for an
  empty remark and `{}` for a disabled health check.
- All four `origin_policy` fields are required. When `BakMode=0`, both origin
  group lists are `[]`.
- `security_policy.port_attributes` preserves every returned `Config` field
  except `Cc` and `PersistenceTimeout`, including original field names, types,
  and values.
- `security_policy.non_website_ai` contains only lowercase `switch` and `mode`.

## Capability-dependent fields

- `application_layer_protection`: enhanced TCP. `ProxyEnable` and both
  `UsTimeout` fields are required. When Proxy is off, both `0/0` and a nonzero
  timeout are valid real states.
- `payload`: Mainland China enhanced TCP IPv4. Both `ModuleEnable` and `Rules`
  are required. An empty rule list is `[]`; a disabled module may retain
  dormant rules.
- `l4_proxy_whitelist`: enhanced TCP IPv4. An empty list is `[]`.
- `advanced_defense`: TCP IPv4. Contains only `Switch` and `Template`.

Omit an entire optional field when the capability is inapplicable. Do not use
an empty object to mean inapplicable.

## Payload rules

Portable rule fields are:

- `Priority`, `RuleName`, and `Action`;
- complete `Conditions` with `Encode`, `Offset.Start/End`, `Pattern`, and
  `Content`;
- `ComputeRules.Ratelimit.Config.Ttl` only for a temporary block.

Do not save RuleId, Owner, Enable, ExpireTime, Vip, Protocol, Port, or empty
ComputeRules. `Pattern` accepts only `contain|not-contain`. A manual regex rule
cannot enter a restorable YAML.

## Forbidden fields

Do not include the source instance ID, EIP, region, resource group, profile,
FunctionVersion, instance specifications or usage, other ports, RequestId,
ProxyStatus, advanced-defense Mode, `Cc`, WebSwitch, WebMode, credentials,
Cookie, Authorization, or signature material.

## Consistency rules

- Compare `real_servers`, primary and secondary origins, and the whitelist as
  unordered sets.
- Match Payload rules by `Priority + RuleName` and compare complete semantics,
  including temporary-block TTL.
- Compare advanced defense only by `Switch + Template`.
- An explicit empty value must come from a successful read. A missing, denied,
  or timed-out field is not empty.
- `ProxyEnable=0 + UsTimeout=0/0` on enhanced TCP requires a disabled Payload
  module, no manual Payload rules, and an empty whitelist; otherwise exact
  restoration cannot preserve `0/0`.
