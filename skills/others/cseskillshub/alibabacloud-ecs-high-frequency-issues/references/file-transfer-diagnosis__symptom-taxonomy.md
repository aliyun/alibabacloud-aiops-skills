# Symptom taxonomy — file transfer (B0 to B6)

This file is the definition set behind `ecs_file_transfer_diagnosis.py classify`.
Enter at B0 and stop at the first branch that fits: the branch decides which
evidence is worth collecting, and collecting evidence for the wrong branch is
how a ticket gets answered with a generic upload tutorial.

| Branch | Definition | Typical customer wording | Exit condition |
|---|---|---|---|
| B0 | Product ownership gate: the transfer does not belong to this ECS instance | "web hosting", "Wanwang", "Wuying", "business licence upload", "renewal review upload" | Product named, boundary stated, routed out; no cloud call needed |
| B1 | Channel misconception: no transfer path has been chosen | "where is the upload button", "what is my FTP password", "how do I transfer", "console has no upload" | One documented transfer path matched to direction, size and OS |
| B2 | Cannot connect at all: port, protocol or reachability | "connection refused", "timeout", "port 22/21/3389", "security group opened but still fails" | The blocking layer named (instance state / security group / listener / customer side) with evidence |
| B3 | Connects but slow or stalled | "slow", "stalls", "takes forever", "drops to", "bandwidth full" | Declared peak compared with observed rate; link-quality part handed to network diagnosis |
| B4 | Transferred but rejected or invisible | "uploaded but 404", "not visible", "wrong directory", "permission denied", "no space left" | One of the three sub-causes proved: wrong path, insufficient write permission, insufficient space or inodes |
| B5 | Protocol mode detail: active/passive, concurrency, client fit | "ECONNREFUSED" after login, "control connection", "forcibly closed", "works with one file only" | Passive range or client mode corrected; SFTP offered as the single-port alternative |
| B6 | Capability boundary and special paths | "download the key pair", "browser download", "cross account", "another region", "API to download", "large file from Workbench" | Boundary stated plainly and a documented alternative given (OSS intermediary, console artifact re-issue, split archive) |

## Intake questions (ask only what the branch still needs)

1. Who transfers what to where: customer workstation, another instance, OSS, or
   the console?
2. Which client and protocol: SFTP/SCP, FTP, RDP drag-and-drop, panel upload,
   Workbench, OSS browser?
3. What is the exact error text, verbatim, and at which step does it appear?
4. What is the file size and count? A single large file fails differently from
   ten thousand small ones.
5. Does the same operation work from another network or another client?

If `classify` returns `no-match`, it defaults to B1. That default is a request
for the intake answers above, not a finding: do not invent a cause before the
answers arrive.

## Branch and error-signature precedence

Error signatures outrank symptom keywords because the literal error text is
harder evidence. When both match, report the signature branch first and the
keyword match as supporting. The literal table is in
`file-transfer-diagnosis__error-signatures.md`.

## What each branch may conclude without cloud data

| Branch | Minimum sufficient evidence |
|---|---|
| B0 | The product named by the customer |
| B1 | The direction, file size and OS, then a documented path |
| B2 | Instance state plus the attached security group, or a customer-side port test |
| B3 | The configured peak and an observed rate, or the customer's own measurements |
| B4 | An in-guest path/permission/space reading, or the customer-pasted output |
| B5 | The server's passive-range configuration or a one-connection test |
| B6 | The capability limit named and the alternative path stated |

Anything less stays `DEGRADED` with the missing reading named in `NEXT_ACTION`.
