# Root causes behind the SSH connection area

Ranked from the support history behind this tier. The ranking is a prior for which
check to run first and how to order the answer; it is never a conclusion. A finding
is only stated when a value returned by an action or a guest command supports it, and
the report says where each value came from.

## Connection times out or never connects

| Rank | Root cause | Discriminating evidence | Typical customer wording |
| --- | --- | --- | --- |
| 1 | The ingress rule for the SSH port is missing, or its authorization object is not the customer's real address - very often the customer deleted or narrowed the rule themselves while hardening the group | `ecs:DescribeSecurityGroupAttribute` | "port 22 times out", "it worked yesterday", "I added my IP and it still fails" |
| 2 | The guest is wedged by resource exhaustion, so nothing answers although the network is fine | Cloud Assistant stops heartbeating; console monitoring shows the spike; load inside the guest | "the whole server froze", "everything is unreachable at once" |
| 3 | A guest firewall drops what the security group allows | `firewall-cmd --list-all`, `ufw status`, `nft list ruleset`, `iptables -S` | "the console says the port is open but I still cannot connect" |
| 4 | The instance is in another account, or in another region, so no check can see it | `ecs:DescribeInstances` returns an empty list while `sts:GetCallerIdentity` succeeds | an instance id that "exists" plus "I already added the security group" |
| 5 | The customer is connecting to an overlay or VPN address (Tailscale, a VPN pool, a private address) instead of the instance address | The address in the command line; the A/B test against the public address | "my VPN address does not answer" |
| 6 | The customer's own network path - carrier, corporate proxy, office egress translation - terminates the connection | Everything on the cloud side is clean, so the S8 checklist is the answer | "my phone works, my laptop does not" |
| 7 | Authentication problems the customer reports as "cannot connect" | The error text names a method or a key, not a timeout | "I can't log in" with no further detail |
| 8 | Security interception, or the aftermath of a malware clean-up | Interception or clean-up context in the description, missing system files | "after I cleaned the virus it stopped working" |
| 9 | Stale static network configuration baked into a custom image | Addressing inside the guest does not match the current VPC addressing | "every instance from my image is unreachable" |

## The session drops in the middle, or after being idle

| Rank | Root cause | Discriminating evidence |
| --- | --- | --- |
| 1 | Resource exhaustion or an out-of-memory kill wedges the guest seconds after login | Load and memory read inside the guest, plus the timeline against the console charts |
| 2 | A whitelist entry holding a private or carrier-grade NAT address never matches, so reconnects keep failing while the customer believes the rule works | `ecs:DescribeSecurityGroupAttribute`, compared with the customer's real egress address |
| 3 | The client path times out: browser WebSocket idle timeout, a proxy, or missing keepalive on the client | A regular interval such as ten minutes, independent of what is typed |
| 4 | The SSH daemon dies mid-session because a required runtime file is missing | `ls` of the login shell, daemon binary and helper library |
| 5 | Interception by a platform security policy after repeated failures | Interception or lockout context in the description |
| 6 | Too little memory for the operating system at that specification | Returned memory against the distribution's own floor |

Two habits of this branch are worth carrying into the answer: line the disconnect
timestamps up with the monitoring data before drawing a conclusion, and state plainly
when the drop cannot be reproduced from the cloud side. The last case is closed by
giving the customer a keepalive command and a client change to test with, and by
installing history tooling so the next occurrence is explainable.

## Authentication fails with `Permission denied`

| Rank | Root cause | Discriminating evidence |
| --- | --- | --- |
| 1 | `PasswordAuthentication no`: the daemon refuses every password | `cat /etc/ssh/sshd_config` |
| 2 | `PermitRootLogin` restricting root with a password while the port is healthy | the same file, plus the login name used |
| 3 | A key pair is bound to the instance and password login is off, while the customer keeps typing a password | key-only `Permission denied (publickey)`, plus credential configuration |
| 4 | `PubkeyAuthentication` commented out or `no`, or `authorized_keys` missing or ignored because of its mode | the config file plus `ls -ld` on the key path |
| 5 | SSH listens on a custom port and the customer targets 22, or the reverse | `ss -tlnp` showing the real port |
| 6 | The password is simply not what the customer thinks: a colleague changed it, a reset was never applied, or the account password was typed instead of the instance password | no technical evidence; confirm with the customer |
| 7 | A login path file was deleted during a security clean-up | `ls` of the login shell and runtime helper |
| 8 | The console key and the customer's local key are believed to be the same credential | a working console login alongside a failing local login |

## What is common to all three

* The customer's stated symptom is reliably weaker evidence than the error text. Get
  the error text.
* The address a customer reports as "my IP" is frequently a private or NAT address.
  Verify it against a public echo service before using it to reason about a rule.
* The instance being healthy and the connection working are different claims. The
  report separates instance state, network permission, guest service, authentication
  and customer path, and states which one failed.
* Where history is needed and no metric action is held by this skill, the console
  chart read by the customer is the substitute, and the report says so.
