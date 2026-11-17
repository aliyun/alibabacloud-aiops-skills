# Handoff Playbook (boundaries and scripts)

This skill is read-only guidance. Whenever the customer's real need requires
entering the guest, a platform-side write, or a commercial / approval decision, the
skill states the boundary, gives the console entry where relevant, and hands off.
This module collects the handoff criteria and the exact wording to use.

Verification date: 2026-08 (per the tier requirements document).

## When to hand off (and to whom)

| Situation | Recognize it when | Hand off to |
|---|---|---|
| Needs commands run inside the guest to close the loop | Self-check steps are exhausted and per-process guest evidence (CPU / I/O / memory) is still required | A guest-level diagnosis capability or a human ticket; this skill never enters the guest |
| Needs a platform-side write | The instance is locked in a way that blocks self-service, or the platform itself must investigate the host hardware (host UnderAssessment / PermanentFailure and the customer cannot move off it), or the underlying network stack must be reset | Human support ticket. Plain host migration is NOT in this row - see the self-service paths below |
| Pure network / link fault | Cloud-side visible facts cannot explain the symptom and the root cause sits in the link layer (VPC routing, public-network path, third-party proxy software taking over routes) | The network skill (for public-network / VPC connectivity use `alibabacloud-ecs-vpc-publicnetwork-troubleshoot`) or a human ticket |
| Disk expansion partition / filesystem, snapshot billing | The symptom is a storage or billing area (for example the console disk resize succeeded but the OS still shows the old size) | A storage / billing skill or human ticket; this skill only explains the two-layer rule |
| Vulnerability remediation, compliance material, invoicing / contracts, compensation adjudication | The need is a security or commercial decision | A security / commercial channel or human specialist |

## Handoff wording (use verbatim, adapt the resource)

Host migration request - give the two SELF-SERVICE paths first, not a ticket:
> Moving an instance to another host has two self-service paths. (1) If you received
> a SystemMaintenance.Redeploy or SystemFailure.Redeploy event, redeploy the instance
> from the ECS console event entry, or with the RedeployInstance operation - the
> instance must be Running or Stopped, must not be on a Dedicated Host, must have no
> security lock and must not be in arrears past expiry. (2) To place the instance on
> or move it between Dedicated Hosts (or onto a deployment set), use
> ModifyInstanceDeployment with the target DedicatedHostId; changing the instance type
> in the same operation is supported. Both paths restart the instance: in-memory data
> is lost, local disks may be re-initialized, the hardware fingerprint changes and
> third-party license-bound software may need re-activation - back up first. I am
> read-only and perform neither operation. A ticket is the right channel only when
> the platform must investigate the host hardware itself or the instance is locked in
> a way that blocks self-service.

Compensation / SLA dispute:
> Availability compensation is application-based, not automatic. You may apply after
> the 5th business day of each month for the previous month, via the SLA claim entry
> (https://usercenter2.aliyun.com/sla/availabilityhome - re-verify before publishing).
> Applying does not guarantee approval; the final decision is made by a human
> reviewer. I can explain the conditions but cannot submit a claim or promise a
> payout.

Guest-side readings (inside the guest):
> Please run the guest-side check yourself (for example `atop`, `iostat`, `top` on
> Linux) and paste the output; I will interpret it against the official rules. I do
> not enter your guest or run commands on it.

Platform-side readings that ARE readable:
> Let me read what the read-only APIs expose: the instance's platform event record
> (event type, lifecycle status, publish / scheduled / finish time) via
> DescribeInstanceHistoryEvents, the Dedicated Host status via DescribeDedicatedHosts,
> and the cloud-disk IOPS / BPS / latency series via DescribeDiskMonitorData. Anything
> outside those (per-process guest I/O, an incident window too old for the disk
> monitor query) comes from the CloudMonitor chart or the guest itself - send the
> reading and I will interpret it.

Network / link symptom:
> The cloud-side facts I can read (instance status, region, bound security groups) do
> not explain a link-layer symptom. For public-network or VPC connectivity, use the
> network troubleshooting skill, which owns that path; I do not probe your host, run
> packet captures, or change routes.

## Two-layer operations (console + OS)

Some customer needs span two layers and are misread as "the platform did not apply
my change". The classic example: a cloud-disk resize succeeds in the console, but the
operating system still shows the old size until the partition and filesystem are
extended inside the guest. This skill explains the two-layer rule and gives the
self-service steps, but the in-guest work is performed by the customer (or handed
off); this skill never enters the guest and never offers to do it on the customer's
behalf.

## Discipline

- Never claim an action was completed ("I have migrated / rebooted / resized for
  you"). This skill is read-only.
- Never assert a host root cause that the read-only APIs cannot see; separate the
  conclusion into "explained / ruled out / not visible" and give the exit for the
  "not visible" part.
- Always cite the rule source and the verification date when explaining an official
  rule.
