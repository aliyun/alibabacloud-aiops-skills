# M4: Pre-Assessment Self-Audit Checklist (S3 companion)

The entry script `scripts/axes/compliance_cert_guide/compliance_inventory.py --regions ...` prints the
**automated** part: facts read from the two whitelisted read APIs only.
This module holds the **manual** checklist that turns those facts into
assessment evidence. Every manual item is a customer action performed by the
customer in the console or inside their own guests - this skill never
executes, changes, or opens anything.

## What the automated table gives you

Per named region, per instance: instance ID, name, running status
(DescribeInstances `Status`, cross-checked against DescribeInstanceStatus),
zone, instance type, OS type (Linux/Windows), network type and VPC, bound
security-group IDs, and public-exposure flags (public IP present / EIP
bound). Empty region = "no instances reported" (a valid finding). Fields the
APIs do not report are printed as `(not reported)`, never guessed.

## Manual checklist

### Identity and access management

| ID | Check | Where to verify (manual) |
|---|---|---|
| IAM-01 | RAM users instead of the root account for daily operations; no shared logins | RAM console -> Users |
| IAM-02 | MFA enabled for console users with administrative rights | RAM console -> Users -> Authentication |
| IAM-03 | Key pairs preferred over instance passwords; unused keys rotated by the customer's policy | ECS console -> Key Pairs; guest SSH configuration is a manual host check |
| IAM-04 | Least-privilege policies for the identities that operate the listed instances | RAM console -> Permissions (compare with the skill's own RAM policy list for what THIS skill needs - only two read actions) |

### Network exposure and boundary protection

| ID | Check | Where to verify (manual) |
|---|---|---|
| NET-01 | Every security-group ID in the table reviewed: no management ports (SSH/RDP) open to broad sources; rule sources tightened to office CIDR or bastion ranges | ECS console -> Security Groups -> each listed group's rules (the rule-listing API is outside this skill's whitelist, so rules are reviewed in the console) |
| NET-02 | Public IP / EIP flags in the table justified: instances marked `yes` either need the exposure or should be moved behind load balancer / NAT designs (customer decision, manual) | ECS console -> Instances -> network details |
| NET-03 | Legacy `classic` network rows (if any) migrated to VPC per the customer's plan | The inventory `Network` column; migration itself is manual |

### Operations audit

| ID | Check | Where to verify (manual) |
|---|---|---|
| OMA-01 | Day-to-day server operations go through a bastion host with session records retained for the assessed period (see the Bastionhost MLPS 2.0 document in M2) | Bastionhost console; customer's own retention policy |
| OMA-02 | Administrative actions on the account recorded and queryable for the assessment window | ActionTrail / operation-log features in the console (product-specific setup is manual) |

### Logging and monitoring

| ID | Check | Where to verify (manual) |
|---|---|---|
| LOG-01 | CloudMonitor agent and metric collection active on the assessed instances | CloudMonitor console; the monitoring-and-logging document in M2 |
| LOG-02 | System / application / security logs retained centrally for the period the assessor requires; retention length is the customer's policy decision | Customer log pipeline (the retention toggle itself is an in-guest or product-side manual action - out of this skill's read scope) |

### Data backup and recovery

| ID | Check | Where to verify (manual) |
|---|---|---|
| BKU-01 | A snapshot plan exists for disks carrying assessed data; snapshots actually exist in the assessment window | ECS console -> Snapshots (this skill does not list snapshots - outside its read whitelist) |
| BKU-02 | Restore procedure tested and recorded | Customer runbook |

### Host / OS

| ID | Check | Where to verify (manual) |
|---|---|---|
| HOS-01 | Image provenance: official or self-audited images; Alibaba Cloud Linux baseline where applicable (see M2 document) | ECS console -> Images; guest OS facts require in-guest checks, which this skill does not perform |
| HOS-02 | Password policy, audit switches, patch level inside each guest | Performed by the customer's system administrators inside the instance - explicitly NOT done by this skill |

### Availability

| ID | Check | Where to verify (manual) |
|---|---|---|
| AVA-01 | Non-`Running` rows in the table explained (stopped for maintenance vs. unexpected); level-3 designs expect redundancy for critical services | The inventory `Status` column plus the customer's architecture notes |

## Reporting rule

In the final answer, keep the two layers visibly separate: "observed by
read-only queries" vs. "manual check items". Never mark a manual item as
passed - the customer's own evidence decides.
