# Acceptance Criteria

## Package

- `SKILL.md` frontmatter contains only `name` and `description`, and uses
  the canonical distributable Skill name.
- `SKILL.md` routes the workflow; export and import business steps exist only
  in their authoritative workflow references.
- Every referenced file exists, every local link resolves, and command Actions
  agree with `related_apis.yaml`.
- The package contains no credential material, obsolete alternate command
  route, simulated execution mode, or duplicated business workflow.

## Export

- Export only manual TCP and UDP ports with `IsAutoCreate=false`.
- Emit one YAML per port with only `port`, `access_policy`, and
  `security_policy` at the top level.
- Preserve exact TCP and UDP PayloadLen, complete origins, remark, health
  check, session persistence, and primary/secondary policy.
- For enhanced TCP, preserve real Proxy, UsTimeout, Payload, and whitelist
  values, including `0/0`, empty rules, empty whitelist, and dormant rules.
- Preserve temporary-block TTL; exclude source RuleId and other derived
  fields; reject a manual regex rule.
- Preserve only Switch + Template for advanced defense and Switch + Mode for
  non-website AI.
- Exclude `Cc.Sblack`, regional blocking, source instance metadata, website
  configuration, and runtime data.
- Require two stable reads of all applicable fields, valid YAML, and file mode
  `0600`.

## Import

- The user specifies a target instance for every YAML. Use a single usable EIP
  directly; ask the user only when multiple usable EIPs exist.
- After the user requests import, execute directly after required validation;
  do not ask for per-field or per-step confirmation.
- Stop the affected port before writing on an automatic-rule conflict,
  capability mismatch, missing field, or unknown state.
- Rebuild a manual port for a backend-port change, clearing a nonempty remark,
  or restoring enhanced TCP `ProxyEnable=0 + UsTimeout=0/0` from another state.
- Use only `ConfigLayer4Rule` for Proxy and UsTimeout, and wait for both read
  paths to converge.
- Write health check and port attributes only after Proxy and
  primary/secondary transitions. Preserve target `Cc`.
- Restore empty and nonempty Payload rule sets, module state, temporary-block
  TTL, and whitelist exactly.
- Compare advanced defense only by Switch + Template. Resolve a shared AI
  conflict once per target instance with the user.
- Report success only after every applicable field matches on a complete final
  readback.

## Security and consistency

- Every cloud API command explicitly carries the selected profile, region, and
  one session User-Agent.
- Never read, display, or save AK/SK, token, Authorization, Cookie, signature,
  signed URL, or profile name.
- Associate by business identity, never array position, and paginate to the
  server total.
- Preserve the distinction among unknown, inapplicable, explicitly empty, and
  failed.
- Leave automatic Payload rules, website configuration, other ports, and
  non-YAML configuration unchanged.

## Correct and incorrect patterns

- ✅ Correct: one YAML contains one manual `(protocol, frontend_port)`
  identity. ❌ Incorrect: combine multiple ports or source-instance metadata
  into one backup.
- ✅ Correct: after the user authorizes import, validate once and restore
  directly. ❌ Incorrect: pause for confirmation before every field or stage.
- ✅ Correct: preserve an applicable empty object or list, and omit a capability
  that is inapplicable. ❌ Incorrect: use an empty value to represent a failed
  or denied read.
- ✅ Correct: declare success only after exact normalized readback. ❌
  Incorrect: treat a RequestId or zero process exit status as restore proof.

## Port evaluation suite

The core end-to-end suite contains four scenario files:

1. Back up the existing manual TCP port.
2. Back up the existing manual UDP port.
3. Restore the TCP fixture to a free frontend port selected in
   `50000..59999`. If occupied, increment by one, wrapping at 59999, until the
   exact `(tcp, frontend_port)` identity is free.
4. Restore the UDP fixture with the same independent selection rule for
   `(udp, frontend_port)`.

The original fixtures are immutable. A restore scenario changes only
`port.frontend_port` in a working copy, performs the complete import and exact
readback, repeats the import to prove zero planned writes when already equal,
then deletes only the manual test port it created and proves it is absent.

All four core scenarios use the configured domain test profile and
`cn-hangzhou`. Backup scenarios are read-only. Restore scenarios must record
the chosen port so every expectation and cleanup targets the same identity.

Supplemental scenarios cover the independent branches that the four core
flows cannot exercise safely or deterministically: bare-port protocol
discovery, an existing output file, multiple target EIPs, an instance-shared
non-website AI conflict and readback, the four principal API error classes,
and exact positive-trigger phrases. Mocked target identities must never expand
authorization to a real cloud resource.

## Delivery evidence

The four core scenarios prove the default-function TCP and UDP workflows,
one-port YAML portability, collision-safe restoration, exact readback,
idempotence, and cleanup. It does not by itself prove enhanced-only Proxy,
UsTimeout, Payload, and L4-whitelist writes when the selected domain-profile
instance reports `FunctionVersion=default`.

Customer delivery therefore also requires current live evidence from an
enhanced TCP IPv4 instance for:

- Proxy on/off with both read paths converged and exact nonzero UsTimeout;
- the real `0/0` rebuild path;
- Payload module on/off, empty and dormant rules, multiple conditions,
  permanent block, and temporary-block TTL;
- empty/nonempty L4 whitelist and advanced-defense on/off;
- no source-list drift across Proxy transitions;
- a second identical import with zero writes.

If that enhanced evidence is unavailable or stale, report the release evidence
as partial rather than claiming the Skill is fully proven.
