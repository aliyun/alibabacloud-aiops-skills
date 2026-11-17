# Console Channel Diagnosis Playbook

The five-layer model, the ticket-proven symptom clusters, and the discipline
for each layer. The entry script implements the routing mechanically; this
file explains the reading so the agent can relay it honestly.

## The five layers

| Layer | What it covers | How this skill gets evidence |
| --- | --- | --- |
| L1 instance | power state, lifecycle transitions, health status, scheduled platform events | `DescribeInstances`, `DescribeInstancesFullStatus` (automatic queries) |
| L2 cloud configuration | public IP presence, bound security groups, expected service ports | instance facts (automatic); security-group RULE detail is a customer console self-check, not an automatic call of this skill |
| L3 channel | which console path is used and what it reports: VNC / management terminal, Workbench, session manager, one-click connect; Cloud Assistant internal channel | `DescribeCloudAssistantStatus`, `DescribeInvocations` history (automatic); VNC / Workbench session establishment itself is human console |
| L4 guest | resource saturation and hang, boot failure and system-file damage, listener and login policy inside the OS | CloudMonitor readings (automatic), ONE gated non-mutating command per confirmation; everything deeper = ask + `explain` |
| L5 customer-local | local egress IP and blocks, security software, carrier / cross-border latency, browser / input method / terminal emulator | never probeable from the cloud side; structured customer self-tests only |

## Opening questions (always first)

1. Instance id and region? (The region is where the console shows the
   instance; a wrong region explains "resource not found" instantly.)
2. OS family, Linux or Windows?
3. Which channel did you try, how far did you get (login page? black
   screen? boot screen?), and what does the error say verbatim? A
   screenshot description is worth more than any guess.

## Symptom clusters and readings

Frequency-ordered from the ticket corpus this tier was distilled from. The
cluster is the CUSTOMER WORDING; the root cause is decided by the evidence
chain, never by the wording.

### C1 "Every channel fails at once" (most common)

Wording: "SSH, VNC and the web terminal are all dead", "VNC shows the
account prompt but Enter gives no password box", "Workbench says my
passwordless login was blocked".

Reading: simultaneous failure of independent channels points at the GUEST,
not at any channel. Two families, told apart by the CloudMonitor leg:

* **Saturation hang** - CPU near the limit, or memory used at/near
  capacity, or load far above the vCPU count: the OS is alive but too busy
  to answer logins. Recovery = snapshot first, then a human restart from
  the console; afterwards install atop so the NEXT occurrence can be
  attributed to a process. Asking "what was running when it started" often
  lands the root cause when the incident time has already passed.
* **Boot / system-file trouble** - no saturation readings, agent
  unreachable, VNC frozen on a boot or loading screen, or login prompts
  that never complete: hand off to the OS-troubleshooting skill with the
  evidence list. Damaged system libraries, a lost `/bin`-style symlink
  chain, a stuck cloud-init, a detached system disk - all recognizable by
  SCREEN BEHAVIOUR, none repairable here.

### C2 "VNC says the resource state does not support this operation"

Wording: exactly that sentence (or its localized equivalent) on opening
VNC, often after the customer pressed restart.

Reading: this is the INSTANCE lifecycle refusing, not the VNC feature
broken. Check `Status`: `Stopping`/`Starting` = transition (wait; if stuck
beyond a normal window, hand off to the instance-state skill - a guest in
heavy I/O or fsck can hang a stop for a long time); `Stopped` = no channel
can attach, starting is a human action and a password reset only takes
effect after the next restart.

### C3 "Connection refused" on any port

Reading: refused means SOMETHING ANSWERED and nothing listened. Three
checks in order (the port triad):

1. the application's REAL listening port vs the port being used (a web
   panel on 5666 reached as 5566 is the classic near-miss - the "channel is
   broken" report was about an application port all along);
2. security-group INGRESS rule for that port (customer console self-check);
3. in-guest listener and its address family - a service bound only to
   `[::]:port` (IPv6 wildcard) refuses IPv4 arrivals; the fix is a guest
   configuration change the customer performs.

Layer separator for the ssh port specifically: the Workbench ONE-CLICK
connect only ever uses port 22 - after a non-standard ssh port change,
exactly that one channel breaks while password login on the new port
still works.

### C4 "Web terminal logs in but nothing works" (capacity pattern)

Wording: "I can open the terminal but I cannot save/create anything".
Reading: login succeeded, so the channel is healthy; a full filesystem is
the usual cause (a gated `df -h` reading or a customer-pasted one proves
it). Capacity cleanup belongs to the disk-capacity skill - this skill
stops at the identification.

### C5 "Workbench is fine, my own computer cannot connect"

Reading: the opposite of what customers conclude. The web terminal reaches
the instance through Alibaba Cloud's internal path; if it works while the
customer's own ssh/RDP fails, the fault sits on the customer side or at the
edge: a local egress IP listed by a blocklist or intercepted by cloud
security controls, local security software, a carrier route, or
cross-border latency. Ladder: telnet to the port from the local machine ->
hotspot retry -> mtr path analysis -> review the security-center IP
whitelist page. Documented in
[channel-matrix.md](console-channel-diagnosis__channel-matrix.md).

### C6 "Wrong characters, severe lag, or the session dropped and killed my task"

Reading: VNC keyboard/input-method quirks are a known terminal-emulation
limit of the browser path: switch the input method to English, switch
browsers, or move to a native client. A web terminal dropping its
connection does NOT reboot the server; foreground processes die with the
session - long tasks belong under nohup/screen or a session manager.

### C7 "The console VPC change fails with InvalidDependence.GrantAccess"

Reading: the instance's VPC is protected by a reverse-access grant chain
created through the Workbench path; the change is refused until those
grants are released. The release is a human console action on the grant
chain (no verified official deep link ships with this package - say so and
route to support if the console path is unclear). This is a
configuration-dependency class, not a channel outage: see
[error-codes.md](console-channel-diagnosis__error-codes.md).

### C8 "Reset the password and it STILL will not log in anywhere"

Reading: check the sequence first - an offline reset only applies on the
next restart; then suspect an in-guest lockout policy behind repeated
failures. Lockout state is NOT auto-inspectable here: the customer runs
the login/account status commands themselves and pastes the output into
`explain`. Disk-attach password repair is a human maintenance action.

### C9 Pure entry / usage questions

Wording: "where is the web terminal entry", "how do I upload a file".
No fault exists; answer from [channel-matrix.md](console-channel-diagnosis__channel-matrix.md) with
the console path and the official documents. A meaningful share of
channel tickets are this.

## Evidence discipline

* Cloud readings are point-in-time: state the metric timestamp from the
  report. After a restart the hang evidence is gone - which is WHY the
  playbook insists on readings before restart, and atop afterwards.
* `DescribeInvocations` is history, never live usage; the only live guest
  reading allowed is one gated whitelist command per confirmation.
* Missing datapoints and unqueried facts are reported as missing. Never
  fill a gap with a remembered value, and never claim security-group rules
  or in-guest listeners were "checked" when they were only ASKED about.
* Confidence: `high` = two independent legs agree; `medium` = one direct
  leg plus consistent facts; `low` = pattern match only. The report labels
  each verdict exactly so.

## Windows and RDP boundary

RDP (3389) symptoms ride the same layering until the channel layer: VNC
onto the desktop works while RDP refuses = the remote-desktop service
area -> hand off to the remote-desktop skill; both dead together = guest
reboot/repair lane. The gated command set carries the Windows read
equivalents (`Get-Volume`, `Get-PSDrive`, drive-free queries) so the same
"logged in but cannot write" pattern is confirmable there too.
