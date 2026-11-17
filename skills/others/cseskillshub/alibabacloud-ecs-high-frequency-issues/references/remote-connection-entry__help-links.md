# Reference Documentation Links (help-links)

Official Alibaba Cloud documentation used by this skill. Every URL below was
reached and checked while authoring this package; the title column is the
English rendering of the document's own subject. Nothing here is a guessed or
synthesised path: if a page could not be verified, it is listed under
"Deliberately not linked" instead of being invented.

Console URLs are entry points, not documents; they require the customer's own
signed-in session and are never fetched by this skill.

---

## 1. Connection channels and how to choose one

| What it is for | Document / entry point |
| --- | --- |
| Overview of every supported way to log in to an ECS instance, and how to pick one | `https://help.aliyun.com/zh/ecs/user-guide/guide-and-best-practices-for-logging-into-ecs-5-methods-and-how-to-choose` |
| The general connection guide (entry page for all methods) | `https://help.aliyun.com/zh/ecs/user-guide/connect-to-instance` |
| Workbench (browser-based terminal) overview | `https://help.aliyun.com/zh/ecs/user-guide/workbench-overview` |
| Workbench, Linux instances | `https://help.aliyun.com/document_detail/147650.html` |
| Workbench, Windows instances | `https://help.aliyun.com/document_detail/147651.html` |
| Workbench access entry | `https://help.aliyun.com/document_detail/108412.html` |
| Session Manager / browser session channel | `https://help.aliyun.com/zh/ecs/user-guide/connect-to-an-instance-by-using-session-manager-2` |
| Session Manager related pages | `https://help.aliyun.com/document_detail/337915.html`, `https://help.aliyun.com/document_detail/330099.html`, `https://help.aliyun.com/document_detail/423617.html` |
| VNC / remote connect from the console | `https://help.aliyun.com/document_detail/25433.html` |
| SSH client tools for connecting to Linux instances | `https://help.aliyun.com/document_detail/51798.html` |
| RDP client (Windows App) for connecting to Windows instances | `https://help.aliyun.com/document_detail/25435.html` |

Why this section exists in a triage skill: the channel semantics in
`references/remote-connection-entry__triage-tree.md` (which channel needs a public IP, which is subject
to the security group, which is subject to in-guest software) are derived from
these pages. The channel table is the reason "the console works but my client
does not" is a legitimate observation and not a contradiction.

---

## 2. Credentials and logon management

| What it is for | Document |
| --- | --- |
| Instance logon credential management (reset password, key pair, VNC-based reset) | `https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management` |

This page is the source of the credential-effectiveness rules quoted in
`references/remote-connection-entry__triage-tree.md` step S4: which credential changes take effect
immediately, which require a restart performed **inside the console**, and how
online versus offline reset differ. The skill only points the customer here; it
never receives, stores, tests, or submits a password or private key.

---

## 3. Network path and security groups

| What it is for | Document / entry point |
| --- | --- |
| Security groups: the practical guide to precise network access control | `https://help.aliyun.com/zh/ecs/user-guide/5-minute-guide-to-security-groups-secure-and-precise-network-access-control.md` |
| Adding a security-group rule (console operation, performed by the customer) | `https://help.aliyun.com/document_detail/2973977.html` |
| Public network access / bandwidth and billing behaviour | `https://help.aliyun.com/document_detail/419460.html` |
| Security group console entry point | `https://ecs.console.aliyun.com` (network section, signed-in) |

The first-match rule precedence implemented in
`scripts/areas/remote_connection_entry/ecs_remote_connection_triage.py` (ascending `Priority`, `Drop` winning
over `Accept` at equal priority) and the local correlation checks in
`references/remote-connection-entry__securitygroup-checklist.md` come from these pages.

---

## 4. SSH failure troubleshooting and guest-side checks

| What it is for | Document |
| --- | --- |
| SSH connection failure troubleshooting (the decision tree and the verbatim client error strings) | `https://help.aliyun.com/document_detail/41470.html` |
| `atop` for looking at historical guest load | `https://help.aliyun.com/zh/ecs/user-guide/use-the-atop-tool-to-monitor-linux-system-metrics` |
| Swap configuration for a Linux instance | `https://help.aliyun.com/zh/ecs/user-guide/how-do-i-configure-the-swap-partition-of-a-linux-instance` |
| "allocate memory" / `fork: cannot allocate memory` at service start | `https://help.aliyun.com/zh/ecs/user-guide/start-a-service-in-the-linux-system-prompt-task-always-the-allocate-memory-what-should-i-do` |

`references/remote-connection-entry__error-signatures.md` mirrors the error strings published on the
troubleshooting page, and `references/remote-connection-entry__guest-selfcheck-commands.md` mirrors the
customer-run commands. Both are documentation mirrors, not inventions: when a
string is not documented, it is labelled as a symptom phrase.

---

## 5. Instance operations that appear in guidance (customer-performed)

| What it is for | Document |
| --- | --- |
| Restarting an instance | `https://help.aliyun.com/document_detail/25440.html` |
| Cloud Assistant status and how to read it | `https://help.aliyun.com/document_detail/2546029.html` |
| Installing / repairing the Cloud Assistant agent | `https://help.aliyun.com/document_detail/64921.html` |
| Creating a single manual snapshot (before a risky restart) | `https://help.aliyun.com/document_detail/25455.html` |
| Snapshot billing (so the customer can judge the cost of that snapshot) | `https://help.aliyun.com/document_detail/56159.html` |
| Deleting a snapshot (cleanup after the fix lands) | `https://help.aliyun.com/document_detail/128131.html` |

These back the risk notices in `scripts/areas/remote_connection_entry/_constants.py` (`RISK_NOTICES`): a
normal stop/restart is expected to take a window of minutes, an in-guest
service restart is not an instance restart, and a snapshot before a reboot is
the cheap insurance the customer can take. The skill reports the links and the
trade-offs; the customer performs the operation.

---

## 6. Account, billing, and security handoff entry points

| What it is for | Entry point |
| --- | --- |
| Billing / overdue balance check (a stopped-by-arrears public path looks exactly like a firewall) | `https://usercenter2.aliyun.com` |
| Security centre / incident review, used by the intrusion handoff | `https://yundun.console.aliyun.com` |
| Report centre for exporting evidence | `https://report.aliyun.com/#/reportCenter/home` |

The intrusion branch never investigates here: it identifies the signal and
routes the customer to the security channel (see
`references/remote-connection-entry__triage-tree.md` section "X. Intrusion suspicion").

---

## Deliberately not linked

Recording these keeps the file trustworthy:

1. **A dedicated Windows RDP "cannot connect" troubleshooting document.** No
   such page was verified during authoring. Windows RDP failures in this skill
   are routed through the protocol split, the security-group check, and the
   VNC fallback, not through a cited RDP runbook.
2. **A cloud-init agent install link** that appeared malformed in the source
   material. A URL that cannot be resolved is not shipped, even if it was
   quoted at us.
3. **Any CIDR for the console-side connection services** (Workbench / Session
   Manager source ranges). The security group must allow those sources, but the
   authoritative ranges are not pinned in this package; the customer is
   directed to the console page instead of to a number that could be stale.
4. **Cloud Monitoring metric names beyond `cpu_total`.** Only the one metric
   with a verified name and namespace is queried; the rest are not invented.
