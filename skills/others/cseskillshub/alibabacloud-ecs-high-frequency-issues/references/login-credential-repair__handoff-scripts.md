# Out-of-scope areas and handoff wording

This skill owns one vertical: is the ECS instance logon credential and account
usable. Everything else is identified, named, and handed off with the wording
below. Identifying correctly **is** the deliverable for these cases; fixing them
is not, and an attempt to fix them here is a scope violation even when it works.

## 1. The handoff table

| Trigger observed | Area it belongs to | Wording to use | What this skill still does |
| --- | --- | --- | --- |
| Port never answers, connection times out before any prompt, "cannot reach the server" | Transport and security group | "The connection never reaches a logon prompt, so this is a connectivity and security-group question rather than a credential one. Confirm the instance is running and review the inbound rules for the remote port." | States that no credential was ever evaluated; gives the console path for inbound rules |
| Instance will not start, or is stuck between states; a repair needs the instance stopped | Instance state | "The instance state itself has to be resolved first; starting, stopping and forced restarts are outside this flow." | Reports the state read from the API |
| Reset fails with a disk-space message; guest has no free space to write | Disk capacity | "The guest cannot write the password change because the disk is full. Space has to be reclaimed or the disk expanded - and expansion has a minimum increment - before the reset can succeed." | Names the blocker and hands off; never clears or shrinks anything |
| Logon works but the session is black, laggy, or a required service was not running | Resource and service health | "The credential is now accepted; the remaining slowness is a resource or service problem, typically memory saturation." | Confirms the credential area closed |
| Ransomware, files encrypted, backup agent not running, account appears renamed or deleted after an incident | Security incident | "Signs point to a compromise. Stop here: no re-initialisation, no guest changes from this flow. Back up with the most recent snapshot and hand this to the security incident process." | Stops, does not remediate, does not recommend destructive actions |
| Weak signal only - an unexpected username inside the guest | Not proof of intrusion | Report the observation and its source. Do **not** assert compromise: an image that ships a custom user is a different thing from a renamed account | Distinguishes observation from inference |
| Panel, site or application password (for example a web hosting control panel), or "how do I open my panel" | Application layer | "That is an application password, not the ECS instance logon credential. This flow does not reset it; the panel's own commands must be run by you inside the instance." | Keeps the two concepts apart; gives no password-changing command |
| Website returns an application error such as a 500 while the instance is healthy | Application code | "The server itself is running normally; the error is returned by the site's own code and has to be checked by whoever maintains it." | Says so plainly instead of escalating |
| Installer or application complains about missing permission, "run as administrator", user cannot use an installed program although they can log on | Application permission / UAC | "Logon is working, so this is a permissions question inside Windows, not an ECS credential problem." | Exits the flow; this is the classic false hit on the word "administrator" |
| Linux user cannot run privileged commands with `sudo`, or root is limited inside a working session | OS permissions | "The credential worked; what is limited is the privilege level. That is an operating-system permissions question." | Hands off to the OS troubleshooting skill |
| SSH key or password authentication rejected in a working SSH session (`Permission denied`) | See note in section 2 | Route on whether a prompt was reached at all | Runs the boundary test first |
| Console key-pair binding for a Windows instance, or "use SSH keys on Windows instead" | Product capability | "The console key-pair binding applies to Linux instances. Self-installing an SSH server on Windows is possible but is not covered by an official page here, so this flow cannot configure it." | States the boundary plus the alternatives that do exist (non-default port, source restriction) |
| How to upload files, how to find the instance in the mobile app, what a plan includes, price or configuration-change questions, DNS questions | Onboarding, commercial, DNS | "Those are separate from the logon credential; here is the console page for the instance itself, and the rest goes to the corresponding channel." | Answers only the "where are the IP, OS and reset entry" slice |
| Snapshot cost, snapshot retention, "what if I skip the snapshot" | Billing, adjacent to the fix | Answer once, in the same breath as the snapshot instruction, then return to the credential issue | Points at the snapshot and billing pages in [help-docs.md](login-credential-repair__help-docs.md) |

## 2. Neighbouring skills, and how to avoid colliding with them

| Neighbour | Overlap | The line this skill draws |
| --- | --- | --- |
| SSH authentication failure (password or key rejected, `Permission denied`) | Highest overlap in this tier | If the SSH handshake reaches an authentication stage, the credential area owns it and LC2/LC4 apply. If no prompt or banner ever appears, it is transport |
| Brute-force / malicious logon attempts | Large overlap | This skill explains the lockout mechanism and hardens access by guidance. The moment there are indications of a real compromise, it stops and routes to the security incident process |
| Linux root or sudo privilege limits | Moderate overlap | Getting in is this skill; what you can do once inside is not |
| General Linux operating-system troubleshooting | Overlap on anything OS-internal | Boot, kernel, network configuration and service faults go to that skill. This one stops at "is the credential and account usable" |
| Disk capacity and expansion | Reached from the reset failure path | Identified and handed off, never repaired from here |
| Instance state diagnosis | Reached from the offline reset path | Identified and handed off |

## 3. Handoff mechanics

- Name the area, name the reason, and stop. Do not perform the neighbouring
  fix "just this once".
- Report the evidence that triggered the handoff with its confidence label, so
  the receiving party inherits facts rather than conclusions.
- Where the customer must act in the console, give the navigation text from
  `../SKILL.md` ("Console navigation") rather than an invented deep link.
- Where this skill cannot see (security-group rules, guest logs, VNC entry
  generation), say which reading is missing and who can perform it. The
  `STATUS: DEGRADED` line exists for exactly this: a named gap, not a guess.
- A handoff never includes a destructive action recommendation. Specifically:
  re-initialising a system disk, deleting snapshots, stopping the instance,
  detaching disks, editing the registry, or forcing a policy change are all
  phrased as "a human evaluates and performs this in the console, after a
  snapshot".
