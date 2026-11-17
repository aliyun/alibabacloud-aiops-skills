# Instance metadata service: rules, what read-only can prove, and the customer checklist

The symptom this module covers: a process inside the instance -- typically
cloud-init, an SDK credential chain or an agent -- cannot read instance metadata
and the failure surfaces as a timeout or as
`Failed to establish a new connection: [Errno 101] Network is unreachable`.

Evidence labels: `api:` = verified against the live read API; `ticket:` = a
support conversation that was read in full; `summary:` = a ticket summary whose
conversation was NOT re-pulled (reported, not verified). Rule wording
cross-checked **2026-08**; response shapes live-verified **2026-09-18**.

## 1. Endpoint facts

- The metadata service is reached from inside the instance over the link-local
  address `100.100.100.200`. Reads are plain HTTP GETs against a versioned path;
  the path used in the reported cases is
  `http://100.100.100.200/2016-01-01/meta-data/instance-id` (`ticket:0003YRXU6P`,
  quoted verbatim from the customer's cloud-init log).
- The address sits in the `100.100.0.0/16` range that the platform reserves for
  in-network services; the internal DNS resolvers `100.100.2.136` and
  `100.100.2.138` are in the same range. A guest-side change that captures or
  rejects that range therefore breaks metadata, internal DNS, or both
  (`summary:00047S4Z0N`, where both resolvers and the metadata address failed
  while public internet access stayed healthy).
- Boot-time consumers make this loud: when metadata is unreachable, cloud-init
  stalls or errors during instance start, which can look like an OS that "does
  not come up" rather than a network fault (`ticket:0003YRXU6P`).
- Token-only access (the hardened form, sometimes called IMDSv2-style: a session
  token must be requested before metadata can be read) is an instance setting.
  This skill can read the current value of the instance's metadata options
  (`HttpEndpoint`, `HttpTokens`) from the instance listing and nothing else:
  enabling it is a change the customer performs, and it is deliberately not
  scripted or submitted here.
- **A returned empty value means "no value was recorded for this instance", not
  "hardening is off"** (`api:DescribeInstances`: instances that never had the
  option set return empty strings). Never infer a configuration from an absent
  field.

## 2. Where the fault actually lives (observed in the source tickets)

| Observed in | Root cause per the ticket | Who could see it |
|---|---|---|
| `summary:000CARW2UA` | a host firewall rule rejecting the `100.64.0.0/10` range blocked service traffic; the fix was a guest-side rule change | only an in-guest reading |
| `summary:00047S4Z0N` | an overlay / VPN tool suspected of taking over the `100.100.0.0/16` route; the ticket timed out before confirmation | only an in-guest reading |
| `ticket:0003YRXU6P` | after a forced reboot following security-group edits, guest network initialization failed and cloud-init could not reach the endpoint | only an in-guest reading (agent worked around it by asking for disk snapshots plus remote-access authorization) |
| `ticket:0003YRXU6P` | the Cloud Assistant agent reported a client-side network block | that is a Cloud Assistant symptom: `alibabacloud-ecs-cloud-assistant-diagnosis` |

The common shape: the cloud-side attributes (status, VPC, attached groups) show
nothing wrong, and the decisive reading is inside the operating system.

## 3. What this read-only skill can and cannot do

Can do:

- Read which region and zone the instance is in, whether it is Running or
  Stopped, which VPC / vSwitch it sits on and which security groups are attached
  -- an **exclusion** step that removes "the instance is in the wrong network"
  and "no group is attached" from the list of candidates.
- Read the instance's current metadata-option values so a hardening question can
  be answered with the real value instead of an assumption.
- Compare `DescribeInstances` status against `DescribeInstanceStatus` for a batch
  of instances (`--status-check`), which is how "the customer is looking at a
  stopped machine" gets separated from "the machine runs but its guest network
  stack is broken".

Cannot do, and must say so out loud:

- It runs nothing inside the instance: not a route lookup, not a firewall dump,
  not a curl, not a package query. It does not read cloud-init logs, and it does
  not open a VNC or session-manager channel.
- It changes nothing: no firewall rule, no route, no metadata option, no policy.
- Therefore, for a metadata-unreachable symptom it can never honestly print
  "root cause found" or "fixed". The strongest permitted conclusion is
  "no cloud-side configuration factor is visible that explains this", followed by
  the checklist below or a ticket hand-off.

## 4. Customer-run self-check (Linux)

Give these as steps the customer executes in their own shell inside the
instance. Each is read-only; the customer removes nothing until they have read
what a check returned.

1. Read the endpoint by hand:
   `curl -v http://100.100.100.200/2016-01-01/meta-data/instance-id`
   -- a working endpoint answers the instance id; a timeout or
   `Network is unreachable` reproduces the symptom outside cloud-init.
2. Check the route for the reserved range:
   `ip route get 100.100.100.200` and `ip route show | grep -E '100\.100|100\.64'`
   -- look for the address being sent to an unexpected interface.
3. Check host rules for a reject covering the reserved ranges:
   `iptables -S | grep 100.` and, where nftables is in use,
   `nft list ruleset` -- look for a REJECT or DROP matching `100.100.0.0/16` or
   `100.64.0.0/10`.
4. List third-party VPN / overlay network software (tailscale and comparable
   tools) and whether it claims that range.
5. Check whether the failing consumer is cloud-init specifically:
   `cloud-init status` and the cloud-init log for the boot in question.
6. If a change is needed (a rule to remove, a route to fix), that is the
   customer's own decision: snapshot the disks first via their own console
   workflow, then change one thing and re-test.

Windows instances: the same facts apply (the endpoint is the same), but no
verified equivalent command set exists in this skill's evidence set, so this
module deliberately does not print one. Ask the customer which OS family the
instance runs (`OSType` is in the listing) and, for a Windows guest, hand the
check to a support ticket instead of guessing PowerShell equivalents.

## 5. Hand-off wording

> This needs readings from inside the instance -- routing, host firewall and any
> third-party network software -- which is outside this assistant's read-only
> scope. Either run the checklist above yourself and send me the output so I can
> re-verify the cloud-side facts, or open a support ticket and authorize remote
> diagnosis; the standard precondition there is a snapshot of every disk of the
> instance, taken by you in the console.

Hand-off targets for lookalike symptoms: in-guest agent or command channel
failures -> `alibabacloud-ecs-cloud-assistant-diagnosis`; security-group rule
changes and port reachability -> `alibabacloud-ecs-access-block-layered`;
web-server behaviour -> `alibabacloud-ecs-web-service-runtime-config`; guest OS
activation or system problems -> the guest-OS skill for that component.

## 6. Documentation gap

This skill's evidence set contains **no verified official documentation URL** for
the metadata endpoint, its version paths, or the hardening option, and
fabricating one would be worse than admitting the gap. Answer from the facts
above, state that the endpoint and reserved-range statements were cross-checked
in 2026-08 against the ticket evidence, and tell the customer to confirm the
current documented wording for token-based metadata access before enabling it on
production instances.
