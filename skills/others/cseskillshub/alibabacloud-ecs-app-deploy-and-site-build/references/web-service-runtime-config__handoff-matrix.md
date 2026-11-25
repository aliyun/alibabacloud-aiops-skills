# Handoff matrix

Where the symptom stops being "web service and runtime configuration" and starts
belonging to someone else. The boundary column is the part that matters: it says
what this skill still does before it lets go, so a handoff is never an excuse for
an unanswered question.

| Symptom | Target | Boundary - what stays here | Evidence |
|---|---|---|---|
| extension install failed, cloud assistant, plugin install, one-click deploy failed, command extension | `alibabacloud-ecs-install-extension` | the install action itself failing (plugin missing, delivery failed, task status abnormal, extension parameters or version) belongs there; **what can be installed on which image, and everything after installation, belongs here** | T-A9825E98, T-F51E65E5 |
| cannot start, stuck stopping, stopped by itself, won't boot, shutdown | `alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis` | instance lifecycle, not web service configuration. This skill still reads the state and says which area it is on | T-E923DA06, T-43513829 |
| disk full, no space, inode exhausted, file count limit, cannot create new file | the disk capacity skill | capacity and inode pressure are diagnosed there; here only the question "is a full filesystem blocking this service" | tier keyword budget |
| disk slow, io latency, bps saturated, performance below spec | `alibabacloud-ecs-high-frequency-issues: resource-bottleneck` | IO performance; this skill only names the resource a service is competing with | T-99F91F5E, T-9DDDFAD4 |
| expand disk, partition not applied, resize not effective | `alibabacloud-ecs-high-frequency-issues: disk-expand-diagnosis` | expansion and partition work | tier list |
| hacked, webshell, virus, malware, unknown admin account, abnormal process | Security Center plus manual security handling | identify and stop the bleeding (snapshot, change passwords, remove the unexpected account, restrict inbound ports), then hand off; removing files or processes is never done here | T-040B35C3, T-D592BBF3, T-CA03A3F6 |
| cannot reach overseas, isp blocked, cross border, outbound ip blocked, latency from another country | the network product and path investigation queue | path, carrier and penalty matters; this skill reports only what the guest side shows | T-48D25F5F, T-A692D630, T-D592BBF3 |
| icp filing, beian, domain blocked in mainland | the filing process | compliance interception, not a service fault | T-713A543E |
| unpaid, overdue, arrears, recharge, bandwidth suspended | billing and account operations | billing state | T-7C096742 |
| sub-account permission, ram policy, grant view access | RAM (custom policy or resource group) | the ECS console has no application-log-level permission; only identify and point | T-6FC28660 |
| migrate server, move wordpress from another provider, cross platform migration | Server Migration Center | collect what must be exported instead (site files, database, PHP version and enabled parameters, Nginx or Apache, database version), then hand off | T-C0934ABB |
| restore from backup, file level restore, snapshot or backup scope | data protection and snapshot tooling | a file-level backup does not restore a runtime environment; reconfiguring it is this skill's scope only as guidance | T-2A482800 |
| ack node, acs cluster, pod cannot schedule, cluster resource | the container service for Kubernetes support path | cluster node scaling and scheduling | T-ABB48381 |
| bt panel, aaPanel, 1panel, third party panel, baota | the panel vendor's own support | not an Alibaba Cloud product; the agent's own wording in the ticket was that they were not familiar with it | T-E24E7F32, T-B0960B66 |
| configure it for me, do it on my behalf, price, discount, promotion | manual handling, or the commercial channel for pricing | this skill does not enter a customer's server to configure anything and does not answer sales questions; it emits the steps instead | T-C03C9EDC, T-6A5E475B |

## How a handoff is worded in a report

The report states three things together, in this order:

1. what was already established here, so the next owner does not repeat it;
2. that the remaining part is handled by the named target, said plainly;
3. what this skill will not do, when the temptation is obvious - restarting the
   service, adding the inbound rule, deleting the malicious file, quoting a
   price.

A handoff never leaves the customer with only "not our problem". If a next step
exists on this side - take a snapshot, note the exact error text, check the
source address of the test - the report names it before pointing elsewhere.

## Overlap that is resolved in this skill's favour

- A one-click deployment that "failed" because the target release does not carry
  that runtime: the support fact is this skill's, the retry of the install action
  is not.
- A container that will not start because the image cannot be pulled: outbound
  reachability and the documented mainland-region mechanism are here; the cluster
  scheduling question is not.
- A site that is slow because the guest is out of memory: the resource pressure
  reading is here, and the instance type sizing advice stays general.
- A "web server is down" report where the instance is merely in the console's
  normal stopping window: this skill reads the state and names the mechanism,
  then hands the lifecycle question over.
