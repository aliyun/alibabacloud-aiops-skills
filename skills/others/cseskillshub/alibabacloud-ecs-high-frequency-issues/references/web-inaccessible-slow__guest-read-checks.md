# In-guest non-mutating checks (level B)

Nothing that runs on the cloud side can see a listening socket, a service state or a host
firewall inside the guest. `ecs:DescribeInstances` and friends never return that information, so
the only automated path is Cloud Assistant (the `run-command` operation dispatched, read back with
`ecs:DescribeInvocations`). That makes this file the permission boundary of the whole skill.

## Rules that govern every entry

1. **One agreement authorises exactly one command.** Before dispatching, state all three: the
   literal command, the blast radius (one instance; nothing is written; live traffic is not
   touched), and how to revert (nothing to revert - these are enumerations and reads).
2. **Only a key from the table below can be dispatched, and only if it is approved.** The
   authoritative list is `GUEST_CHECKS` in `../scripts/areas/web_inaccessible_slow/_constants.py`; print it with
   `python3 ../scripts/areas/web_inaccessible_slow/ecs_web_access_check.py --list-guest-checks`. Do not widen the list on
   your own authority.
3. **No chained, piped or redirected forms.** Each entry is a single argv. A request that needs
   `|`, `;`, `&&` or `>` is refused and converted into a paste-back request.
4. **Nothing in this table mutates state.** No restart, no rule change, no truncation. Log
   reading is a `tail`; clearing a log is a level D prohibition.
5. Every result is returned base64-encoded in the `Output` field of the invocation and is decoded
   and secret-masked by the script before it reaches the report.

## Approval state as shipped

The batch low-risk whitelist authored for this skill family covers disk-capacity tooling
(`df`, `du`, `lsof`, `findmnt`, `stat`, `ls`, `wc`). **None of the web-path checks below is
literally listed there**, and `systemctl` is literally excluded. Therefore **every entry ships
with `approved: False`**, and the honest behaviour of the skill is:

```
requested guest check not on the approved list
 -> refuse, and say why
 -> emit the execute-and-paste-back sheet below
 -> print STATUS: DEGRADED with the reason
```

A reviewer who approves a key flips `approved` to `True` for that key alone. The dispatch path is
already implemented and needs no further change.

## The ten checks

| Key | Command | Layers | Approved | What it proves |
| --- | --- | --- | --- | --- |
| `listening-sockets` | `ss -lntp` (fallback `netstat -lntp`) | L5 | no | Which ports listen at all, and whether the bind is `0.0.0.0`/`::` or only `127.0.0.1`/`::1` |
| `firewall-rules` | `iptables -S` (fallback `nft list ruleset`) | L5 | no | Host packet-filter rules and any fail2ban chain that drops the tested port; enumeration only |
| `service-state` | `systemctl status nginx` (fallback `service nginx status`) | L5 | no | Is the web service alive, and enabled at boot after a reboot |
| `route-table` | `ip route` (fallback `route -n`) | L5 | no | Return path for the client source, and a Docker bridge stealing a subnet |
| `docker-networks` | `docker network ls` (fallback `docker ps`) | L5 | no | Extra bridge subnets that overlap the customer network or shadow the published port |
| `self-curl` | `curl -sv --max-time 10 http://127.0.0.1/` | L5, L6 | no | Loopback proves the listener and the application answer; add `-H "Host: <site>"` for name-based virtual hosts |
| `host-files` | `cat /etc/hosts` | L2, L5 | no | Local name overrides inside the guest, and the TCP wrappers deny list to inspect next |
| `resolver-config` | `cat /etc/resolv.conf` (fallback `nslookup example.com`) | L2 | no | Which name server the guest really uses, for the self-resolution test |
| `web-error-log` | `tail -n 80 /var/log/nginx/error.log` (fallback `/var/log/httpd/error_log`) | L6 | no | Last errors behind a 5xx or a blank page; append-only read, truncation is prohibited |
| `connection-sources` | `ss -H -tn state established` (fallback `netstat -an -t`) | L8 | no | Connection count and abnormal source ranges, i.e. the attack versus capacity split |

`service-state` deserves its own note: `systemctl` is the single most useful command for this
scenario and engineers did use `systemctl status firewalld` in a reviewed ticket, yet the current
whitelist excludes `systemctl` outright. The skill therefore does not pretend to be allowed to
run it. It asks the customer, and it records the conflict here so the reviewer can resolve it
deliberately instead of the agent working around it.

## Dispatch mechanics (only for an approved key)

- `Type` is `RunShellScript` for Linux. **Windows is guidance-only** in this release
  (`WINDOWS_DISPATCH_ENABLED = False`): no Windows command set was approved, so for an
  IIS/Windows instance the skill emits manual steps instead - IIS site bindings (port and host
  name), application pool state, Windows Firewall inbound rules for the site port, and the IIS
  failed-request tracing log location.
- The instance is passed as the repeated parameter `InstanceId.1`, not as a JSON array.
- `Timeout` is set on the command itself; the client additionally caps each call
  (`GUEST_TIMEOUT = 90 s`, `CLOUD_ASSISTANT_TIMEOUT = 60 s`) and polls
  `ecs:DescribeInvocations` at a bounded interval with a bounded number of polls.
- If the Cloud Assistant agent is missing or offline, degrade in this order: authorised
  console/VNC session, then the paste-back sheet. Never ask for a password to get in.

## Execute-and-paste-back sheet

Emit this when the key is not approved, when Cloud Assistant is unavailable, or when the customer
prefers to run it themselves. It is the same content the script prints.

```
Please run these two commands inside the instance (they only read state, they change nothing),
then paste the full output back into this ticket:

  1) <command>          # <purpose>
  2) <fallback>         # if command 1 is not installed

What we are looking for: whether port <port> listens, and on which address; whether any rule
drops it; and what the last error lines say. We will not ask for, or accept, any password in
this conversation.
```

Number the requests, ask for at most the four checks that the current error string routes to, and
say which layer each answer would close. Asking for all ten at once is how a ticket stalls.
