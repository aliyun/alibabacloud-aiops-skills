# In-instance observations: what may be issued, and what may not

This is the approval record for every observation the skill can ask for. It is
the authority behind `guest-plan` and `guest-run`, and it is deliberately
narrower than the list of things a human agent would run.

Two approval states exist:

- **approved** - the command is inside this batch's signed low-risk non-mutating
  command set, so `guest-run` may dispatch it through Cloud Assistant after the
  announce-and-confirm gate. One command per call.
- **pending** - the observation point belongs to this tier (the tickets prove
  it), but the exact command line was not signed into this batch, because the
  injected command list is worded for the disk-capacity tier. Until the batch
  owner signs it off, the skill prints the command for the customer to run and
  paste back, and records the item as unread with `STATUS: DEGRADED`. A pending
  entry is an approval boundary, not a failed call.

Nothing in the pending list is ever executed "because it looks harmless", and no
substitute command is invented for it.

## Approved, issuable by this skill

| id | command | what it proves | reversibility |
|---|---|---|---|
| `disk-space-facts` | `df -h` | a full filesystem is blocking startup or writes | prints usage only |
| `disk-inode-facts` | `df -i` | inode exhaustion, where "no space" is reported but bytes are free | prints counters only |
| `mount-facts` | `findmnt` | a data directory looks empty because the disk is not mounted | prints the mount table |
| `deleted-open-files` | `lsof +L1` | space did not return because a deleted file is still held open | lists descriptors |
| `path-size` | `du -sh <absolute path>` | one named log or data directory is the consumer | prints one size |
| `path-facts` | `stat <absolute path>` | owner and timestamps behind a permission-denied read | prints metadata |

`path-size` and `path-facts` take exactly one absolute path through `--path`.
The path is rejected if it contains `..`, shell metacharacters, or does not
start with `/`.

## Pending sign-off, customer-run only

| id | command the customer runs | why the observation point is here | ticket evidence |
|---|---|---|---|
| `service-listening` | `sudo netstat -tunlp` | decides "Connection refused" between no-listener, loopback-bound listener, and missing rule | T-9C6BB0CC, T-0C2557E6 |
| `web-config-test` | `sudo nginx -t` | a version switch left nginx unhealthy and nobody had looked at the config | T-E923DA06 |
| `service-log-tail` | `sudo journalctl -u nginx -n 50 --no-pager` | in one ticket the decisive timeline was in the application's own log, not the system log | T-0C2557E6 |
| `service-state` | `systemctl status nginx --no-pager` | loaded/enabled state, read without changing it | T-43513829, T-CA03A3F6 |
| `runtime-version-facts` | `python3 -V` | a Python 2 vs 3 mismatch, and a Node.js version question | T-8D57CDFD, T-F51E65E5 |
| `php-extension-facts` | `php -m` | a missing zip symbol blocked every PHP version installed | T-B0960B66 |
| `installed-package-facts` | `rpm -qa \| grep -i libzip` | dependency library older than the runtime expects | T-B0960B66, T-A9825E98 |
| `memory-and-oom-facts` | `free -m && dmesg -T \| grep -i oom` | seventeen OOM events killed mysqld, php-fpm and nginx | T-0868235B |
| `container-facts` | `docker ps -a` plus `docker inspect` of restart policy and mounts | a database that returns to its image state after each restart | T-1EB845AD, T-F4F68F93 |
| `registry-mirror-config` | `cat /etc/docker/daemon.json` | which mirror, if any, the daemon is configured with | T-C59D3702 |
| `image-pull-selftest` | `docker pull hello-world` | splits "timed out" between the daemon's outbound path and the site | T-C59D3702 |
| `site-address-config` | `grep -R -E "siteurl\|home" wp-config.php` | a site address written as an IP caused the redirect loop | T-F701AEBC |

The service name in the three nginx-worded commands is an example: it is the
service the tickets in this tier were about. Ask which service the customer is
diagnosing and give them the same command with that name, rather than assuming.

## Windows

No Windows observation is issuable by this skill. The cmdlets that would read
IIS role state, application pool state or the event log are not in this batch's
approved set, so on a Windows instance every in-instance reading comes back as
"ask the customer, or send a console screenshot". Where the reading only exists
in a screenshot, say so instead of asserting the cause.

## The gate before an approved command runs

`guest-run` prints what it is about to do and stops. It dispatches only when
`--confirmed` restates what the customer agreed to. Before dispatch it then
re-checks, in order:

1. the instance still resolves, and is `Running`;
2. the guest is Linux, matching the command's `os_types`;
3. the command passes the whitelist **and** the blacklist (see below);
4. exactly one instance is targeted, and one command is sent per call.

Polling `DescribeInvocations` is bounded: a fixed wait interval, a maximum poll
count, and a wall-clock timeout. A timeout is reported as "the command may still
be finishing", never as a failure of the customer's system.

## Guardrail: whitelist and blacklist, both required

A command is dispatched only if its first token is one of
`df`, `findmnt`, `lsof`, `du`, `stat`, **and** it matches an approved command
line verbatim (or with the validated path substituted), **and** it contains none
of the side-effect patterns (`SIDE_EFFECT_COMMAND_PATTERNS` in
`scripts/axes/web_service_runtime_config/_constants.py`). The blacklist covers at least: file removal and
truncation, redirection (`>`, `>>`), in-place editing, package installation,
`systemctl start|stop|restart|reload|enable|disable|mask|unmask|daemon-reload`,
`service ... start|stop|restart`, `journalctl --rotate|--vacuum`, `docker
rm|rmi|stop|start|restart|kill|prune|run|exec|update|create|build`, `kubectl
delete|apply|scale|cordon|drain|taint|edit|patch|rollout`, `iisreset`, `reg`,
`netsh`, `net start|stop|user|localgroup`, the PowerShell `New-`, `Set-`,
`Remove-`, `Clear-`, `Stop-`, `Start-`, `Restart-`, `Install-`, `Uninstall-`
verbs, `taskkill`, `sc start|stop|config|delete|create`, `mount`/`umount`,
partition and filesystem tools, `chmod`/`chown`/`setfacl`, and clock changes.

Chaining (`|`, `;`, `&`) is rejected. Rejection is the safe answer: a false
rejection costs one manual step, a false acceptance changes a customer's system.
