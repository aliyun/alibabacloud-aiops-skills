# Documentation links

Two groups, deliberately separated. **Group A** came out of the documentation search
pass run for this tier and can be quoted as-is. **Group B** appeared in ticket
conversations: the wording around them is authoritative customer-facing guidance, but
the links were not re-verified by that search pass, so confirm a Group B link still
resolves before putting it in front of a customer.

The runtime copy of this table is the `DOC_LINKS` constant in
`scripts/areas/host_intrusion_cleanup/_constants.py`; the key names below are the constant's keys, so a report can
name the exact entry it used. Never hand a customer a link that is not in one of
these two groups, and never reconstruct a documentation URL from memory.

## Group A - verified by the documentation search pass

| Key | Title | Use it for | Link |
| --- | --- | --- | --- |
| `security-overview` | ECS security overview | The shared-responsibility boundary: what the platform secures and what the customer owns. Answers "the platform should have protected me" | https://help.aliyun.com/zh/ecs/user-guide/security-overview.md |
| `best-security-practices` | ECS security best practices | The authoritative source behind the hardening list | https://help.aliyun.com/zh/ecs/user-guide/best-security-practices.md |
| `mining-virus-guide` | Mining virus protection and handling | The main runbook for the mining / virus / trojan branch | https://help.aliyun.com/zh/ecs/user-guide/mining-virus-protection-and-handling-guide.md |
| `data-backup` | ECS data backup and protection | Backup options and recovery guidance for the ransomware branch | https://help.aliyun.com/zh/ecs/user-guide/data-backup.md |
| `data-protection-schemes` | ECS data protection schemes compared: snapshot versus file backup | The exact confusion between snapshots and file backup - scope, what each restores, how each is billed | https://help.aliyun.com/zh/ecs/user-guide/select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md |
| `network-bandwidth` | ECS public and internal bandwidth | Bandwidth anomaly context when a customer reports unexplained traffic | https://help.aliyun.com/zh/ecs/user-guide/network-bandwidth.md |
| `what-is-ecs` | ECS overview | Background only, when the customer is unsure what an instance or a disk is | https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md |

The same search pass also returned generic ECS pages (feature overview, instance
restart, web-server quick starts, preemptible-instance data retention). They are not
carried into this skill: none of them answers an intrusion question, and quoting them
would only add noise to an incident reply.

**Known gap.** The search pass did not return a dedicated article for ransomware
emergency response, for the snapshot-rollback console procedure, or for webshell
cleanup. Those steps are therefore given from the console entry points named in the
report plus the Group B links below, and are described as console procedures rather
than quoted from a document.

## Group B - sourced from ticket conversations, re-verify before quoting

| Key | Title | Use it for | Link |
| --- | --- | --- | --- |
| `create-snapshot` | Create a snapshot | The evidence snapshot, and the automatic snapshot policy that prevents the next incident | https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot |
| `rollback-disk` | Roll back a disk by using a snapshot | The manual rollback procedure the account holder performs, with its irreversibility warning | https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot |
| `ransomware-protection` | Comprehensive protection plan against ransomware attacks | The anti-ransomware capability discussion, including which edition is needed | https://help.aliyun.com/zh/security-center/use-cases/comprehensive-protection-plan-against-ransomware-attacks |
| `hardening-list` | Security hardening recommendations | The six-item hardening list in its published form | https://help.aliyun.com/document_detail/60787.html |
| `snapshot-billing` | Snapshot billing | The billing notice that always accompanies the gated evidence snapshot | https://help.aliyun.com/document_detail/56159.html |
| `delete-snapshot` | Delete a snapshot | The manual cleanup step that stops evidence snapshots from billing | https://help.aliyun.com/document_detail/128131.html |
| `windows-bandwidth` | Troubleshoot high bandwidth usage on Windows instances | The Windows branch of a bandwidth-anomaly complaint | https://help.aliyun.com/zh/ecs/support/troubleshooting-and-solving-the-problem-of-high-bandwidth-usage-in-windows-instances |
| `illegal-domain-info` | What to do if a domain name contains illegal information | Defacement cases where the domain itself was flagged | https://help.aliyun.com/zh/dws/support/what-to-do-if-a-domain-name-contains-illegal-information |
| `uninstall-aegis` | Uninstall the Security Center client | Only for the isolation-loop check when a protection rule is suspected of blocking legitimate traffic; the customer performs it | https://help.aliyun.com/document_detail/68616.html |
| `virtual-host-malware-1` | Malicious files on a cloud web hosting site (part 1) | The handoff pack for a non-ECS hosting product | https://help.aliyun.com/document_detail/85221.html |
| `virtual-host-malware-2` | Malicious files on a cloud web hosting site (part 2) | Same handoff | https://help.aliyun.com/document_detail/211342.html |
| `virtual-host-malware-3` | Malicious files on a cloud web hosting site (part 3) | Same handoff | https://help.aliyun.com/document_detail/312524.html |
| `marketplace` | Alibaba Cloud Marketplace | Third-party data recovery, decryption and security operations - named as a channel, never as an endorsement, and always with the caution that no service can guarantee decryption | http://market.aliyun.com/ |
| `sas-console` | Security Center console | Where the customer handles, whitelists or quarantines an alert; this skill guides but never operates it | https://yundun.console.aliyun.com/ |

## Quoting rules

1. Quote a link only when it matches what the report actually concluded. A ransomware
   report does not need the bandwidth article.
2. Never quote a price, a retention limit, an edition capability or an unblock window
   from memory. Point at the pricing or product document and at the console page that
   shows the customer's own values; published numbers change.
3. Never invent a document, a section anchor or a shortened URL. If the answer is not
   in one of these two groups, say so and describe the console path instead.
4. Console paths are described, not linked, unless the link is in this file: the
   customer's console layout depends on their product edition and language.
