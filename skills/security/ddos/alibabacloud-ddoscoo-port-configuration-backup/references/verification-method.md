# Verification Method

## Decision rule

- Export: generate a YAML only after two consecutive reads of every applicable
  field normalize to the same desired state.
- Import: read back the affected dimension after every write, then perform one
  complete per-port read after all steps.
- A RequestId, zero exit status, or accepted command is not configuration
  equality.
- Missing, denied, timed-out, and unknown values are not empty, disabled, or
  inapplicable values.

## Identity matching

Associate every response by business identity:

- port: `InstanceId + Protocol + FrontendPort`;
- Payload and whitelist: `EIP + Protocol + Port`;
- non-website AI: target instance;
- before a delete, freshly prove `IsAutoCreate=false` for the port or the
  target current manual RuleId for the Payload rule.

Never associate by array position. Pagination must reach the server-reported
total. `DescribeLayer4Rules.Offset` is the number of records already read, not
a page number.

## Field comparison

| Dimension | Equality rule |
|---|---|
| Base rule | BackendPort and Remark exactly equal; RealServers equal as an unordered set; IsAutoCreate is false |
| Health check | Complete object equality; distinguish `{}` from missing |
| Port attributes | Every YAML field and PersistenceTimeout exactly equal; target `Cc` unchanged |
| PayloadLen | Exact Min and Max for both TCP and UDP |
| Primary/secondary origin | Exact BakMode and CurrentIndex; both IP groups equal as unordered sets |
| Proxy | Both read paths reach expected ProxyEnable and ProxyStatus; exact two-field UsTimeout |
| Payload | Exact ModuleEnable; match manual rules by Priority + RuleName and compare Action, Conditions, and temporary-block TTL; ignore generated RuleId |
| Whitelist | Complete server-normalized list equal as an unordered set |
| Advanced defense | Compare only Switch + Template; ignore optional derived Mode |
| Non-website AI | Compare only Switch + Mode; do not compare WebSwitch/WebMode |

## Proxy convergence

After `ConfigLayer4Rule`, read both status paths every 5 seconds for up to
90 seconds. Enabling requires `1/on` from both, and disabling requires
`0/off` from both. Continue polling while they conflict; fail if they still
conflict at the deadline.

After every Proxy convergence, also compare BackendPort, the complete
RealServers set, and Remark. Proxy and primary/secondary transitions may reset
health checks and port attributes, so write and verify those two dimensions
only after every transition has finished.

## Allowed and forbidden normalization

Ignore only:

- server-generated Payload RuleId, Owner, Enable, ExpireTime, Vip, Protocol,
  and Port;
- empty ComputeRules on permanent-block or observe rules;
- advanced-defense Mode;
- ordering differences in semantically unordered sets.

Do not ignore:

- temporary-block TTL;
- dormant Payload rules while the module is disabled;
- `0/0` versus `3/600` or another nonzero timeout while Proxy is disabled;
- empty remark, health check, rule list, or whitelist versus a missing field;
- any other writable field that remains different after server normalization.

## Final success

A port succeeds only when all of the following are true:

1. The current rule still has the exact confirmed manual port identity.
2. Every applicable access and security field in the YAML has a complete fresh
   readback.
3. Every field equals the desired state under this document's normalization.
4. Target `Cc`, automatic Payload rules, website configuration, and other
   ports remain unchanged.
5. Shared AI was retained or changed exactly as the user decided, and the
   result does not describe it as port-exclusive.

Otherwise report the failed field, expected value, actual value, and stopping
step. Do not automatically roll back writes that already succeeded.
