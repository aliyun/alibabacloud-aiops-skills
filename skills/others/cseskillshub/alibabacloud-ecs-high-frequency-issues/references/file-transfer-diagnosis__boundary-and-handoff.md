# Boundary and handoff — file transfer area

This area owns one symptom: a file moving between a customer workstation and an
ECS instance (or between an instance, another instance, OSS and the console)
that fails, is refused, is slow, or lands somewhere unexpected. Everything else
is identified, named, and handed off with the facts already verified.

## Handoff table

| Signal | Route to |
|---|---|
| SSH or RDP fails with no transfer involved | the remote connection skill for that protocol |
| Account locked after failed logins, key pair or password changes | `area:login-credential-repair` |
| Packet loss, latency or cross-border route as the main complaint | `alibabacloud-mtr-network-diagnosis-customer` |
| Bandwidth peak, temporary upgrade or billing mode | `area:bandwidth-modify-guide` |
| Disk space or inode exhaustion as the main complaint | the disk capacity governance skill |
| A disk that grew in the console but not in the OS | `area:disk-expand-diagnosis` |
| Instance stuck starting or stopping | the instance state skill |
| Disk latency or throughput below spec | the disk IO performance skill |
| Overdue balance stopped the instance or its bandwidth | account and billing support |
| Web Hosting FTP accounts, Wuying Cloud Desktop, order review uploads | that product's own console and support |

A handoff carries: the customer's verbatim complaint, the instance id and
region, the transfer method and port, what was already checked with its result,
and the one question the receiving area must answer. Never hand off a bare
symptom.

## Ownership rules

1. **RDP login failure** — the connection fault belongs to the remote connection
   area. The file-transfer area keeps only the file-moving consequence: once the
   session works, the drag-and-drop or Workbench path is in scope. When a changed
   RDP port is suspected (ticket `T-16BA2895` documents `33089`), say so as a
   hint to the connection area; do not diagnose the session here.
2. **Credential reset or key re-issue** — out of scope. The login credential
   area owns it. Workbench or SFTP guidance may resume once credentials work.
3. **Bandwidth and billing** — out of scope. This area may report an observed
   rate, but the peak change, temporary upgrade and billing mode belong to the
   bandwidth area.
4. **Disk space and inodes** — the reading is welcome evidence for B4, but the
   conclusion and remediation belong to the disk capacity area.
5. **Object storage** — using OSS as an intermediary is in scope as guidance;
   bucket policy, ACL and OSS-side errors are handed to OSS support.

## Overseas regions

For instances outside mainland China (for example United States regions),
remote assistance on the instance is restricted by policy: even human support
cannot operate them remotely. Announce this restriction, then work from
customer-pasted output. Do not attempt the guest command channel there.

## Wording

State the boundary in one sentence and the route in the next:

> This is a remote-desktop connection fault rather than a file-transfer fault.
> The connection area owns it; here is what it will need: ...

Do not answer the other area's question "just this once". A partial answer from
the wrong area is worse than a clean handoff, because the customer then has two
conflicting diagnoses.
