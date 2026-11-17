# BT panel access triage — the five layers

The customer says "the panel will not open". That sentence covers five
different places the traffic can die, and the support threads of this
scenario prove every layer independently blocks people: work each layer to a
verdict of **excluded / hit / no-evidence** before naming any cause. The
`triage` subcommand runs the cloud-side parts automatically and prints the
reading it still needs for the rest; the order below is the order the script
walks.

## Precheck — whose instance, which region (automatic, read-only)

`DescribeInstances` resolves the customer's id or IP; `GetCallerIdentity`
stamps the account. Zero matches is NOT "the instance does not exist":
queries only see the calling account and the named region, and case
T-4B98459C had the panel in one account and the domain work in another.
Ask for the region shown in the console selector; never guess it.

Then `DescribeInstancesFullStatus` (health, scheduled events) and
`DescribeCloudAssistantStatus` (can we read anything inside at all) run. A
not-Running instance explains everything and ends the walk early; an offline
agent means the guest layer degrades to customer-pasted readings — say
`STATUS: DEGRADED`, keep the cloud evidence, hand over the self-check list.

## Layer 1 — access admission

Traffic must be admitted three times before the panel ever sees it:

1. **Security group (cloud side).** The bound group ids come automatically;
   rule detail has no verified query in this scenario, so the reading is the
   customer's console list of inbound rules. The comparison that matters is
   *rules vs the panel's ACTUAL port*, not vs 8888. Fix = customer adds the
   TCP rule for that port with the narrowest source that fits; recovery is
   then re-tested. Cases: T-8095CBCB (8888 never opened), T-64C4EEC1 (source
   IP narrowed to a stale exit IP).
2. **OS firewall (guest side).** firewalld/iptables readers are outside the
   low-risk whitelist: customer self-check `os_firewall_state`
   (`firewall-cmd --state`, `iptables -S`). Disabling or opening them is a
   manual change the customer performs. Cases: T-45CF3415, T-14A38F29
   (double local block while the cloud group looked open).
3. **The panel's own ban list.** A working panel can still block the
   customer's current IP through its security plugin — server-side, invisible
   to every cloud query. Self-check `panel_ban_list`; the block is lifted inside the panel.
   Case: T-943A6E7E.

## Layer 2 — address and port

No cloud API can see which port the panel listens on, and in the field it is
frequently NOT 8888: cases ran on 39575, 51973 and 19356. Trusting the
customer's remembered URL or a "8888 allowed" screenshot sends the diagnosis
the wrong way (T-952279A8: "8888 does not open" while the panel served
51973).

Recover the entry from inside the guest — the customer's own session, because
`bt` commands sit outside the whitelist:

- `bt default` → prints the panel address with its real port, plus
  username/password lines; report back the address line only, never the
  credentials;
- `bt 14` → external and internal addresses with the current port and entry
  path.

Then compare three numbers: the port in the customer's URL, the actual
listening port, and the ports admitted in layer 1. `used-port` vs
`actual-port` mismatch is the single most common "panel is down" that isn't.

## Layer 3 — service and file layer

Split by what evidence can reach:

- **File layer (whitelisted probes, consented).** Do the panel's key files
  exist, and do the certificate files the web error names match the real
  directory? `stat`, `ls`, `wc -l` against the paths from the error wording —
  after the disclosure and one confirmation. Case T-76855857: the config
  pointed one directory level off (missing `www`); T-84281A4D: `port.pl`
  gone. A missing file is a *repair* decision — the repair itself is a
  manual step, this skill only re-verifies read-only.
- **Service layer (customer readings only).** Unit state
  (`systemctl status nginx`), panel process liveness, dependency versions
  (`openssl version`, `pip show urllib3` — case T-C714FE28's incompatibility)
  are all outside the whitelist: print the self-check template, collect the
  paste. Hangs that a service restart clears (T-13B097B7, T-4C614B5F) belong
  to this layer — the restart is the customer's action, never this skill's,
  and the reminder is: snapshot first, you create it in the console.
- Recurring service deaths point down into resources → hand off with the
  layer evidence to the resource area.

## Layer 4 — platform layer

The instance can be perfect and still unreachable:

- **Lifecycle and scheduled events**: proven automatically by
  `DescribeInstancesFullStatus`; if it shows events, the platform layer is
  hit and the console event page is the customer's next stop.
- **Overdue account**: pay-as-you-go bandwidth stops and every public port
  goes dark (T-C9ABB457). No billing query is verified here: recognise the
  signature, hand the customer the billing-overview self-check.
- **DDoS blackhole**: all ports dead on one IP while Running is
  blackhole-shaped (T-86E76038); it lifts on its own after the attack, and
  one instance's blackhole never touches another (T-C3DB3C57) — say that
  plainly. Records and durations belong to the anti-DDoS area.
- **ICP filing**: an interception page on domain access, or assets breaking
  after a cancelled filing (T-36495FE9), is compliance state, not a panel
  fault.

## Layer 5 — customer-local

Only when the layers above are excluded or green: browser cache and
extensions, the customer's changed exit IP against a narrow allow list,
proxy or VPN on the office side. The close sequence: incognito window,
another browser, another network (phone hotspot), `curl -v` from the
customer's machine pasted back (self-check `local_retest`). Cases T-13C89CBC
and T-8BC236C5 both recovered client-side — the server had been fine all
along.

## Degradation rules (hold at every layer)

- Agent offline, dispatch refused, or the customer declines in-guest
  execution → `STATUS: DEGRADED`: keep every cloud finding, print the exact
  read-only command for the customer's own session, continue on the pasted
  reading. Never claim a reading the skill did not get.
- Any query denied (`NoPermission` / `ImplicitDeny`) → name the action, show
  the statement from [ram-policies.md](ram-policies.md), stop there.
- Empty result (instance not visible) → boundary note first (account and
  region are the likely answers), conclusion second.
