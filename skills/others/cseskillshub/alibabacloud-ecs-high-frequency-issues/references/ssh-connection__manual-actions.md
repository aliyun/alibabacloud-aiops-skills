# Human actions and handoffs

Everything on this page is performed by a human, in the console or in an operating
system session the customer controls. The skill states the step, the exact command
where a command is involved, and the risk; it does not run any of it. Notation such
as `<instance-id>`, `<region-id>` or `<port>` marks a value filled in from the
diagnosis.

## Before anything that can change the instance

Take a snapshot of every disk the customer needs to keep, and wait for it to
complete. This is the standing order for every action below, and it is the order the
support conversations in this tier followed every time an engineer was granted access
to a machine.

* Snapshot overview: `https://help.aliyun.com/zh/ecs/product-overview/snapshots-1`
* Create a snapshot: `https://help.aliyun.com/document_detail/25455.html`
* What snapshots cost: `https://help.aliyun.com/document_detail/56159.html`
* Delete a snapshot afterwards: `https://help.aliyun.com/document_detail/128131.html`

Snapshot capacity is billed, so the customer decides when to remove old ones.

## Restart the instance

State all four points before a restart, in this order:

1. A restart interrupts every service on the instance and drops existing sessions;
   production traffic should be moved first.
2. Anything held in memory and not written to disk is lost.
3. The instance is unreachable for the minutes the restart takes, and a machine that
   is wedged by resource exhaustion may take noticeably longer than usual to come
   back.
4. A restart releases pressure but does not identify the cause: without `atop` or the
   CloudMonitor agent installed afterwards, the next occurrence will have no history
   at all.

Restarting or stopping an instance is a console action performed by a human.

## Edit the SSH daemon configuration

Only from a session that stays open (VNC, or the second SSH terminal), and only after
a snapshot. The shape of the change is:

```text
1. back up the file
2. set the option that the diagnosis identified, for example
   PasswordAuthentication yes
   PermitRootLogin yes
   Port 22
3. validate the file syntax before applying it
4. restart the SSH service from the still-open session
5. open a NEW terminal and confirm login works before closing the good session
```

Restarting a service ends existing SSH sessions. If the new configuration is wrong,
the still-open session is the only way back, which is why step 5 is written that way.
This skill neither edits the file nor restarts the service, and asks the customer not
to run a `sed` one-liner against it blind: a single line written by a script is enough
to lock everyone out of a machine.

## Set a new instance password

Password login uses the **instance** password, not the Alibaba Cloud account
password; confusing the two is a recurring reason for a "wrong password" complaint
with a correct memory of the password.

* Change the logon password of an instance:
  `https://help.aliyun.com/zh/ecs/user-guide/reset-the-logon-password-of-an-instance`

An offline password change requires a reboot to take effect, and the reboot carries
the risks listed above. After a password change that did not help, check who else
holds credentials for the instance: in this tier's history a "my password stopped
working" case ended with a colleague having changed it.

## Bind or replace a key pair

* Instance logon credentials:
  `https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management#d63a004e87306`
* Attach a key pair to an instance: `https://help.aliyun.com/document_detail/59085.html#80f5f39cc1ep3`

A key pair bound to an instance replaces password expectations, and the private key is
held by the customer, not by Alibaba Cloud.

## Explain the Workbench key misconception

A key managed in the console for Workbench and the private key file on the customer's
laptop are two different credentials. Logging in successfully through the browser does
**not** prove that the local key file works, and `Server refused our key` from a local
client is a different problem from a successful console session.

* How the password-free console login works (temporary key pair):
  `https://help.aliyun.com/zh/ecs/user-guide/workbench-password-free-login-principle-temporary-ssh-key-pair.md`
* Workbench overview: `https://help.aliyun.com/zh/ecs/user-guide/workbench-overview.md`
* Choosing among the login methods:
  `https://help.aliyun.com/zh/ecs/user-guide/guide-and-best-practices-for-logging-into-ecs-5-methods-and-how-to-choose.md`
* Connection method selection: `https://help.aliyun.com/zh/ecs/user-guide/connect-to-instance.md`
* Session Manager as a password-free path that needs no open port:
  `https://help.aliyun.com/zh/ecs/user-guide/connect-to-an-instance-by-using-session-manager-2.md`

## Log in through VNC when SSH is unusable

VNC reaches the console of the instance and works when the network path to the SSH
port is broken, so it is the fallback for every branch of this skill.

* Log on to an instance by using VNC:
  `https://help.aliyun.com/zh/ecs/user-guide/log-on-to-an-instance-by-using-vnc`

Two interface details cost time in real sessions and are worth stating up front: the
`login:` prompt is asking for the operating system user name, and the `Password:`
prompt does not echo characters - typing produces no visible output, which customers
routely report as "the terminal is frozen".

## Add an address to the security management policy whitelist

Repeated failed logins can trigger a platform-side interception policy. The whitelist
lives under the security management policy page of the console (accessed through
`https://yundun.console.aliyun.com/`, then the IP whitelist tab). Add the customer's
real public egress IPv4, never the address their operating system reports for its own
interface.

This is a security product page: the skill neither reads nor changes it, and points
the customer to the console or to a human.

## Install history so the next incident can be explained

* `atop` for Linux, which keeps process and memory history across a restart:
  `https://help.aliyun.com/zh/ecs/how-to-use-the-linux-system-atop-monitoring-tools`
  (the same guide is reachable under `https://help.aliyun.com/document_detail/101877.html`
  and through the use-cases path
  `https://help.aliyun.com/zh/ecs/use-cases/use-the-atop-tool-to-monitor-linux-system-metrics`;
  quote one, not all three)
* CloudMonitor agent, so the console charts have data even when the guest is
  struggling:
  `https://help.aliyun.com/zh/cms/cloudmonitor-1-0/user-guide/install-and-uninstall-the-cloudmonitor-agent-for-cpp`
* Configure swap on a Linux instance, for memory pressure that is understood rather
  than accidental:
  `https://help.aliyun.com/zh/ecs/support/how-do-i-configure-the-swap-partition-of-a-linux-instance`

Installing packages, editing swap and changing the instance specification are human
actions. A memory upgrade is a specification change: ECS cannot grow memory alone.

## Fix a missing system file

A missing login shell, SSH binary or runtime helper library after a security clean-up
is restored by a human - typically by recreating the symlink or reinstalling the
package - after a snapshot, and together with a security review of how it disappeared.
This skill reports the missing path and hands off; it does not recreate files.

## Handoffs this skill performs

| Situation | Where it goes |
| --- | --- |
| Instance not `Running`, or stuck in `Stopping` or `Starting` | `area:instance-state-diagnosis` |
| Disk IOPS or throughput at the limit of the specification | `area:resource-bottleneck` |
| Disk or inode capacity, or a resize that did not take effect | the capacity and expansion skills of this family |
| A request for a general ECS inspection | `alibabacloud-ecs-diagnose` |
| Mining, malware, interception by Security Center, deleted system files, brute-force lockout | Security Center or a human security engineer |
| Instance not visible to the calling account | the owning account, or switch credentials |
| Windows RDP, account lockout or an NTFS question | a human: the checks here are analogous, not equivalent |

## Where this skill's evidence stops

* No external probe service is called, so "reachable from another network" cannot be
  asserted; it is proposed as an A/B test for the customer.
* No monitoring or metric action is held, so utilisation is requested from the
  customer's console charts or from a VNC session.
* Nothing inside the customer's laptop, home router or carrier path can be inspected;
  the customer-side checklist in [decision-tree.md](ssh-connection__decision-tree.md) is what is
  offered instead.
