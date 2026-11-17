# Host compromise: read the alarm, then hand off

This skill **identifies** the intrusion area and hands it off. It does not scan,
quarantine, delete, patch, reinstall or roll back anything. That split is not
bureaucracy: cleanup is destructive, irreversible and needs an on-machine
operator, and the correct tool for it is either Security Center, the
`alibabacloud-mining-attack-diagnosis` skill, or a human engineer.

## 1. Which alarm means what

| Platform signal the customer quotes | What it actually says | Next step (human) |
|---|---|---|
| Brute-force success or many failed logins | An administrative port is reachable from the internet and passwords are guessable | Narrow the security group to an allow-list, move to key-based sign-in, then check what ran after the successful login |
| Mining program / worm / suspicious program detected | Something is already executing in the guest | Security Center alarm page, full-disk scan; a free trial of Security Center is the normal first move, plus a reputable antivirus on Windows |
| Webshell or backdoor file reported | The web tier can be driven remotely; the "attack" the customer sees may be the attacker's own traffic | Remove the file **after** snapshotting, fix the upload or plugin vulnerability that planted it |
| "Outbound attack detected, access to other servers' TCP port blocked" | The platform cut **this** instance's outbound path because it was attacking others; often an exposed Redis, database or mail service | Explain the cause and effect, treat it as compromise, and use the penalty release page only after remediation |
| Ransomware-encrypted data | Recovery is a backup question, not an attack question | Snapshot the current disk, roll back from an older snapshot if one exists, or route to paid third-party recovery; no decryption is offered by the platform |
| Illegal-content / URL-shielded notice | A served URL broke the rules, frequently planted through the hole above | Delete the reported URL, prove it returns 404, then apply to release the penalty |

## 2. Two statements that are always wrong

* "Security Center raised nothing, so we were not attacked." A host-side alarm
  product is not a sensor for inbound volume, and the reverse is equally false:
  an alarm does not mean the platform is obliged to clean the machine.
* "I paid to fix the vulnerability, so the block should be lifted." Vulnerability
  fixing, content penalties and DDoS blackholes are three unrelated mechanisms;
  paying for one changes none of the others.

The platform's stated responsibility boundary is hardware, network and the
underlying service. Above the operating system, hardening, patching, credentials
and application code belong to the customer. Say this once, neutrally, and move
straight to what can still be done.

## 3. Preserve first, act second

Intrusion tickets are won or lost on evidence:

1. Take a snapshot of every disk **before** any cleanup, reboot, patch or
   engineer sign-in. State that snapshots bill by capacity and that deleting them
   later is a separate manual step.
2. Never reboot to "fix" the symptom before the connection and process readings
   are captured; a reboot destroys the only copy of the evidence.
3. If the access logs, login records or scheduled-task entries are **gone**, that
   absence is itself a finding worth recording; say so instead of concluding that
   nothing happened.
4. To find the entry point, ask what was installed: a third-party or nulled
   application with a known backdoor is the most common cause, and no cloud-side
   query will ever reveal it.

## 4. Guest-side readings, taken by the customer

This skill does not run commands inside the operating system. Print the exact
read-only command, ask for the output, and interpret what comes back:

* `ss -tunap` or `netstat -ano | findstr :<PORT>` (Windows) - who is connected
  and which process owns it.
* `lsof -nP -i | grep <PEER_IP>` - whether a suspicious peer is really being
  served right now.
* `tasklist | findstr <PID>` - what that process actually is.
* `ps aux --sort=-%cpu | head` and a memory/inode/`df -h` check - the resource
  exhaustion that is mistaken for an attack more often than real attacks are.
* Top source addresses in the access log for the incident hour, counted and
  ranked, compared with a normal hour.

Long-running packet capture is **not** offered as a suggestion: it can fill the
disk, and in documented cases still failed to identify the offending process. If
the customer wants it, it is their decision made with a human engineer.

## 5. When to stop and hand to a human

* The customer says they cannot operate the console or a command line. Do not
  coach them through destructive steps; open a human ticket with the evidence
  pack attached.
* Any request to change source code, decrypt data, file a report, waive a fee,
  or accelerate a penalty release.
* A platform-side network path suspected to be broken: this skill can only
  produce the exclusion evidence (instance Running, rules correct, no blackhole
  event, guest listening) for a human to escalate with.
* Credentials: **never** ask for or accept an account password, panel login or
  key in a chat. If the customer volunteers one, tell them to change it, decline
  it, and use the proper authorisation flow instead.

## 6. Hardening list to hand over with the case

Restrict 22 and 3389 to your own egress address; publish only 80/443; strong
unique passwords plus keys; patch the high-severity vulnerabilities listed in
Security Center after snapshotting; a recurring snapshot policy; deploy a
history-collecting agent such as atop so the next incident can be read back in
time; configure swap so memory pressure degrades slowly instead of wedging the
box; keep the OS and web stack updated. The consolidated checklist and the swap
walkthrough are linked in `references/attack-blackhole-diagnosis__evidence-checklist.md`.
