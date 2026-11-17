# Handoff boundaries

This skill owns exactly one area: **verifying a host intrusion, gathering evidence,
judging recoverability, and guiding cleanup and hardening.** Everything else is
identified, named and routed - never absorbed, and never answered half-way with a
guess.

Two rules make the routing trustworthy:

* **Identify, do not absorb.** An out-of-area request gets one clear sentence naming
  where it belongs and what evidence to carry over. Do not start collecting evidence
  for an area this skill does not own; the customer ends up with a partial answer and
  a second queue to join.
* **Preserve before you route.** If the incident is real, the evidence snapshot and
  the report still matter to whoever picks it up. Finish the class A evidence pass,
  hand over the session id, then route.

## Routing table

| What the customer is actually asking | Where it goes | Evidence to attach |
| --- | --- | --- |
| Deep mining-attack analysis: pool infrastructure, IOC sweep, attacker attribution across many hosts | `alibabacloud-mining-attack-diagnosis` | The mining alert rows and the exposure findings this run already collected |
| An operating-system fault with no intrusion signal (kernel panic, service will not start, package or permission damage, no Security Center alerts for this instance) | `alibabacloud-ecs-linux-os-troubleshooting` | The statement that the alert list for this instance came back empty, plus the alert scan's account scope |
| Disk space or inode exhaustion, "the disk is full", cleanup to free space | `area:disk-expand-diagnosis` | The symptom wording that triggered the route. This skill dispatches no capacity readings at all |
| A resize that did not take effect, a partition that did not grow | `area:disk-expand-diagnosis` | The symptom wording; note that intrusion evidence, if any, was already reported |
| Slow disk IO, latency or IOPS complaints | the disk performance and IO tier (`area:resource-bottleneck`) | The symptom wording and the incident window |
| Instance will not start, is stuck between states, or will not stop | `area:instance-start-stop-anomaly` | Whether encryption or a malicious process was found - a host that will not boot *because* system files were encrypted stays in this skill's ransom branch |
| Volumetric attack, CC attack, traffic black-holed | the DDoS/CC tier, through the human channel | When the traffic symptom started, and the fact that the alert list showed no intrusion |
| Brute-force attempts and blocking a malicious source address | `area:sas-alert-vulnerability` | The exposed management ports and the logon alert findings. Adding the deny rule itself is a manual console step |
| "Unblock my server", a penalty lift, an appeal against a violation block | the customer's own self-service release application on the Security Center penalty records page (`https://yundun.console.aliyun.com/?p=scnew#/sc/event/resources`); the human channel only after that application is rejected | The alert list, the moment public connectivity was lost, and what cleanup and hardening was completed. This skill cannot lift a penalty and cannot submit the application; the platform decides the review and no time window is predicted |
| Re-installing or replacing the operating system after an infection | human channel (the operating-system replacement tier) | The evidence snapshot id and the reason a clean install was recommended |
| Security Center product operations: handling or whitelisting an alert in the console, a tamper-protection false positive, a failed automatic fix, a paid-capability question | Security Center console plus the human channel | The edition and capability findings from the version config, and the alert rows that could not be auto-handled |
| A cloud web hosting (virtual host) or other non-ECS product with malicious files | the hosting product's documentation and its own ticket queue | The product-form check result. There is no remote logon and no ECS API surface on those products |
| Rolling a disk back from a snapshot | the account holder, in the ECS console | The chosen recovery point, the current-state evidence snapshot id, and the irreversibility warning |
| Decrypting ransomware-encrypted data | third-party specialists via the Alibaba Cloud Marketplace | The statement that no pre-incident backup exists, if that is what the evidence showed |
| Refunds, unsubscription, contracts, invoices, withdrawal, liability, lawyer letters, an official ransomware certificate | human channel | The preserved evidence report and the session id. Technical facts only; no commercial commitment |

Sibling skill names above are the ones this batch ships or plans. When a name is not
yet live in the customer's environment, fall back to the human channel with the same
evidence - the routing sentence still holds, only the destination changes.

## Sentences to say

Keep them short, factual and free of blame. Templates:

* Capacity area: "What you are describing is disk space and inode usage rather than an
  intrusion. That is handled by `area:disk-expand-diagnosis`; I have
  already confirmed whether Security Center sees an intrusion on this instance, and
  here is that result."
* Penalty: "Your instance's public access was restricted by a platform security
  penalty triggered by the infection - it is not a network fault. I can show you the
  evidence and the cleanup steps. Once the host is cleaned and hardened, you submit
  the release application yourself on the Security Center penalty records page
  (`https://yundun.console.aliyun.com/?p=scnew#/sc/event/resources`) - I cannot submit
  it, the platform decides the review, and I will not predict how long it takes. If
  that application is rejected, it goes to the support appeal channel."
* Non-ECS product: "These two servers are cloud web hosting, not ECS. There is no
  remote logon on that product: malicious files are removed through the hosting
  control panel's file manager or over FTP. Here is the entry point."
* Commercial or legal: "That part is a commercial question, so it goes to the human
  support channel. What I can do here is preserve the technical evidence - the alert
  timeline, the exposure findings and the snapshot inventory - and give you the report
  to attach."
* Recovery is impossible: "There is no snapshot or file backup from before the
  encryption, so the platform cannot restore this data and does not decrypt
  ransomware-encrypted files. Third-party recovery services are listed in the Alibaba
  Cloud Marketplace; no service can guarantee decryption. What we should fix now is
  the backup retention and the entry point, so the next incident is recoverable."
* Out-of-whitelist reading: "That reading is outside what this skill is allowed to run
  inside your instance. Please run `<command>` yourself in Workbench or over SSH and
  paste the output here - I will interpret it."

## Mixed requests

Customers routinely arrive with two areas at once: ransomware plus a full disk, a
mining penalty plus a resize question, a defacement plus a refund demand. Handle the
intrusion part here, state the boundary for the rest in the same reply, and attach the
evidence to both routes. Never let the second area pull this skill into an action it
does not own.
