# Boundary Rules Library (SWAS product-boundary wording)

Human-readable version of the embedded knowledge base that
`scripts/axes/swas_boundary_guide/swas_boundary_guide.py --rules` prints (machine copy:
`BOUNDARY_TOPICS` in `scripts/axes/swas_boundary_guide/_constants.py`). Every rule below is wording
distilled from real Simple Application Server (SWAS) support tickets; each
card lists its source ticket ids and the verified official doc links. Rules
marked **[summary evidence]** come from ticket summaries whose full dialogue
was not re-verified -- present those as ticket wording, never as an official
policy quote. Only the URLs printed here may be cited; do not invent links
for topics marked "no verified link".

Topic keys (for `--rules --topic <key>`): `product-identity`,
`spec-terminology`, `migration`, `connection`, `network-access`, `commerce`,
`lifecycle`.

## 1. product-identity -- what Simple Application Server is

| Rule | Source tickets | Docs |
|---|---|---|
| Simple Application Server instances are cloud virtual machines, not physical machines. | 000ACRDNT2 | [What is Simple Application Server](https://help.aliyun.com/zh/simple-application-server/product-overview/what-is-simple-application-server) |
| Simple Application Server and ECS are two different products: there is no in-place conversion and no plan swap between a SWAS instance and an ECS instance. | 0001FS19PN | [What is Simple Application Server](https://help.aliyun.com/zh/simple-application-server/product-overview/what-is-simple-application-server) |
| When both products coexist in one account, keep them apart: ECS ids start with `i-`, SWAS ids are 32-character hex strings, and the ECS OpenAPI surface cannot see SWAS resources. | 000EARHWU7, 0005PRAZHW, 000B9RJ2PC | [Manage SWAS with the Alibaba Cloud client](https://help.aliyun.com/zh/ecs/user-guide/use-alibaba-cloud-client-to-manage-simple-application-servers.md) |
| If a genuinely physical server is wanted, the matching product is ECS Elastic Bare Metal Server (priced higher than ordinary cloud servers); quoting is a commercial conversation, not a technical one. | 000ACRDNT2 | [Elastic Bare Metal Server overview](https://help.aliyun.com/zh/ecs/user-guide/elastic-bare-metal-server-overview) |

Customer-facing answers for this topic: state the product form (cloud, not
physical), then answer the follow-up (ECS difference, bare-metal pricing via
the sales channel). Never promise a price.

## 2. spec-terminology -- plan wording such as "2-core 2G"

| Rule | Source tickets | Docs |
|---|---|---|
| "2-core 2G" means 2 vCPU and 2 GiB memory; the second figure in a plan name is the instance memory size. | 000GJRX0P0 | [SWAS instance families](https://help.aliyun.com/document_detail/2861773.html) |
| SWAS memory varies by instance family: general-purpose and international families run 0.5 GiB to 16 GiB; agent-dedicated and CPU-optimized families reach up to 64 GiB. | 000GJRX0P0 | [SWAS instance families](https://help.aliyun.com/document_detail/2861773.html) |
| ECS economy/shared families (such as the economy-type e instance behind the 99 CNY activity) are shared-CPU families; compare instance families before judging price or performance. | 0001FS19PN, 00085RZ8GE | [Shared instance families](https://help.aliyun.com/zh/ecs/user-guide/shared-instance-families.md) |

## 3. migration -- migration and region-change boundaries

| Rule | Source tickets | Docs |
|---|---|---|
| SWAS does not support changing the region of an existing instance; a region move means buying a new instance in the target region and migrating data. | 00094RH5HX | [Migrate servers](https://help.aliyun.com/zh/ecs/user-guide/migrate-servers.md) |
| Cross-region SWAS migration path: (1) make a custom image of the source server, (2) copy the image to the target region, (3) use the copied image to create a new server there. | 00094RH5HX | [Migrate servers](https://help.aliyun.com/zh/ecs/user-guide/migrate-servers.md) |
| SWAS-to-ECS migration runs through sharing the custom image with ECS and launching an ECS instance from it; the ECS default instance family in that flow may be lower-spec than expected (`ecs.sn1.medium` was observed in a ticket), which explains price and configuration surprises. **[summary evidence]** | 000DGRCMD9, 00085RZ8GE | [Migrate servers](https://help.aliyun.com/zh/ecs/user-guide/migrate-servers.md) |
| Hard precondition for image-based migration: target system disk >= source system disk. A 40 GB target cannot receive a 50 GB source, so the 99 CNY activity plan often fails this check. | 0001FS19PN | [Migrate servers](https://help.aliyun.com/zh/ecs/user-guide/migrate-servers.md) |
| Image-based moves may carry a price difference and can void renewal at a promotion price; for cost-sensitive customers the fallback is manual migration. | 0001FS19PN | no verified link (console wizard guidance) |
| Public websites hosted in mainland-China regions need ICP filing before serving mainland visitors. | 00094RH5HX | no verified link (stated in ticket dialogue) |

Decision support for this topic lives in
[references/swas-boundary-guide__migration-paths.md](migration-paths.md); the script mode is
`--migration-check`.

## 4. connection -- remote-connection and OS boundaries

| Rule | Source tickets | Docs |
|---|---|---|
| Linux instances connect over SSH; Windows instances over Remote Desktop (RDP). Using mstsc against a Linux SWAS instance cannot work -- the OS must become Windows first if a desktop session is required. | 0003YS837P, 000EARHWU7 | [Reset a SWAS server](https://help.aliyun.com/zh/simple-application-server/user-guide/reset-a-simple-application-server) |
| Changing the OS (SWAS "Reset System" / ECS "Replace Operating System") replaces the system disk: ALL data on it is erased and cannot be recovered by the platform; back up first. The public IP address stays unchanged. | 0003YS837P, 000EARHWU7 | [Reset a SWAS server](https://help.aliyun.com/zh/simple-application-server/user-guide/reset-a-simple-application-server), [Replace the OS of an ECS instance](https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance-1) |
| After switching to Windows, first boot may take 5-10 minutes before RDP accepts connections; wait before concluding the change failed. **[summary evidence]** | 000EARHWU7 | no verified link (ticket wording) |
| RDP file transfer needs local drive redirection enabled in the client (mstsc: Local Resources -> More -> Drives); the message that the current connection cannot use the file-transfer function points at client-side or local-network limits, not cloud-side configuration. **[summary evidence]** | 0004PS4R06 | no verified link (ticket wording) |

Full matrix and warnings: [references/swas-boundary-guide__connect-methods.md](connect-methods.md);
script mode `--connect-check`.

## 5. network-access -- cross-border reachability and bandwidth boundaries

| Rule | Source tickets | Docs |
|---|---|---|
| Access between overseas regions and the Chinese mainland crosses international links: delay and packet loss are expected link behavior, not instance load. Collect evidence with the public multi-node ping probe before drawing conclusions. | 00094RH5HX, 0006SRSDLE | [Boce ping probe](https://boce.aliyun.com/detect/ping) |
| A provider-side reachability check passing does not prove the customer's local network can reach the instance, and vice versa; when both sides disagree, the dispute is resolved through a support ticket with probe evidence attached, not by online assertion. | 0005PRAZHW | [Boce ping probe](https://boce.aliyun.com/detect/ping) |
| SWAS carries a shared peak-bandwidth plan: during busy hours contention can throttle effective bandwidth (1 Mbps was observed in a ticket), which can make management-panel pages fail to load; SWAS is not positioned for workloads needing strong public-network quality guarantees. **[summary evidence]** | 000AWRHMSJ | no verified link (bandwidth QoS doc not verified for this skill) |

Escalation wording for reachability disputes: hand over the structured
evidence (instance id, region, status, probe method and results) via a
support ticket; never promise unblocking, compensation, or a root-cause
verdict.

## 6. commerce -- promotion and refund rule boundaries

| Rule | Source tickets | Docs |
|---|---|---|
| New-customer promotion tiers (such as the 68 CNY/year SWAS tier) are limited to accounts that have never generated an order record; after a refund the order record remains, so re-purchase at the promotion price is no longer possible. | 000BSRL35W | no verified link (activity rule quoted in ticket dialogue) |
| The 99 CNY/year ECS activity requires real-name verification, is limited to one instance per person, and is not renewable at the activity price after an image-based replacement; the activity page holds the authoritative current terms. | 0001FS19PN | [99 CNY/year ECS activity page](https://www.aliyun.com/daily-act/ecs/99program) |
| The 5-day unconditional refund benefit is limited to one use per year per product per account; using it on SWAS excludes reusing it on ECS in the same year. **[summary evidence]** | 0001ZSAG86 | no verified link (quote as ticket wording, point to the official policy page) |
| Restoring promotion eligibility, price negotiation, refunds and releases are commercial processes: never executed by tooling, only escalated to human sales/support channels. | 000BSRL35W, 000B9RJ2PC | no verified link |

Handoff wording and the "never promise an outcome" discipline:
[references/swas-boundary-guide__commerce-rules.md](commerce-rules.md).

## 7. lifecycle -- expiration and release self-service

| Rule | Source tickets | Docs |
|---|---|---|
| Expiration dates and renewal orders are visible in the console (instance list / order center) without calling support; guide self-service first. **[summary evidence]** | 00073S1MFZ | [Manage SWAS with the Alibaba Cloud client](https://help.aliyun.com/zh/ecs/user-guide/use-alibaba-cloud-client-to-manage-simple-application-servers.md) |
| A free-trial instance expiring soon can simply be left unrenewed; proactive manual release is not required. **[summary evidence]** | 000B9RJ2PC | no verified link |
| Billing-side states (renewal orders, unsubscribe status) are outside the verified read-only surface of this skill; they degrade to console guidance. | (design boundary) | no verified link |

## Evidence discipline (applies to every topic)

1. Quote the rule wording; do not paraphrase prices, quotas or eligibility
   conditions beyond what the card states.
2. Cite only the doc links printed on the card. Cards marked "no verified
   link" have none: guide via console paths instead of inventing a URL.
3. **[summary evidence]** cards must be presented as support-ticket wording
   pending re-verification, not as official policy.
4. When a customer asks for proof (for example of a security detection),
   cite the detection record's source; never assert an unfounded cause.
