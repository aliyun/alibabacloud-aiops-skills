# Permission-area diagnosis knowledge (S1 to S4)

Knowledge embedded to keep answers evidence-based. Nothing here is a ticket finding: **no
representative ticket or conversation was supplied for this tier**, so the ordering, the frequency
and the customer error strings below are unconfirmed design mappings. Where a claim needs a reading
from the customer's instance, say so and go and get the reading.

## Step 0 - take the customer's own words, then route

Record verbatim: the exact error line, which account ran which command, whether the customer reached
the instance by SSH, VNC or a console session, and which path is affected. `classify` maps that
wording to S1..S4 or to a handoff. If nothing matches, ask for the error line; do not classify from
assumed wording.

## Step 1 - settle the control plane before believing "permission"

`preflight` runs the non-mutating reads. A permission fault cannot be established while any of these
is unresolved:

| Reading | What it rules out or in |
|---|---|
| `DescribeInstances` returns nothing | wrong region, wrong id, or another account owns it - stop, confirm with the customer, never switch region silently |
| `Status` not `Running` | nothing inside the guest can be inspected; hand off to `alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis` |
| `DescribeInstancesFullStatus` events, `ExpiredTime`, a scheduled stop or a non-`Ok` health status | an expiry or an event lock presenting as a logon failure; that is lifecycle or billing, not sudoers |
| Image and OS name | which values are expected in `perm-baseline.md`; the baseline is image-dependent |
| `DescribeCloudAssistantStatus` not ready | the in-guest channel is unavailable, go to the manual path (step 4) |
| Security groups **bound** to the instance | this skill reads the list, not the rules; port 22 reachability stays a manual console check |

## Step 2 - decide which layer is refusing

Two independent authorization systems exist, and mixing them up is the single most common framing
error on this area:

* **Cloud side (RAM)** decides whether an OpenAPI call is allowed - including whether a RAM user may
  run Cloud Assistant commands at all.
* **Guest side (root, sudo, su, file modes)** decides what a Linux account may do inside the
  instance. Being an instance owner in the console grants nothing inside Linux.

`sts:GetCallerIdentity` fixes which principal the cloud reads ran as, which is what separates "my
RAM user cannot do this" from "my Linux account cannot do this".

Three controls are frequently reported as faults. Each is expected behaviour, and confirming one
ends the diagnosis:

1. **A RAM policy prohibiting root as the initial user** of a Linux instance. Creation with root as
   the initial user is blocked by design; it is not guest corruption.
2. **Hardening guidance that avoids direct root logon.** If the image or the sshd configuration
   follows it, root logon is refused while `sudo` by a normal user still works - the refusal is the
   control working.
3. **A RAM user not authorized for Cloud Assistant commands.** The command never reaches the guest,
   so the symptom looks like an in-guest failure while nothing inside the instance is wrong.

Only after those three are excluded does a guest reading become the interesting evidence.

## Step 3 - scenario trees

### S1 root logon refused or credential lost

1. Step 1 and step 2 first; root logon refused by a control is not a fault.
2. `guest-plan --scenario S1` proposes `stat /etc/ssh/sshd_config`, `stat /root`,
   `findmnt -o OPTIONS,TARGET`. Note the boundary: only **existence, mode and owner** of the sshd
   configuration are read; `PermitRootLogin` and `PasswordAuthentication` **content** needs `cat` or
   `grep`, which the whitelist refuses, so the customer runs it.
3. Outcomes: control confirmed (explain, link the guidance) / file or `/root` ownership wrong
   (S3 or S4 territory) / credential genuinely lost (step 5 manual path).

### S2 sudo authorization missing

1. Fix the two-systems question from step 2 before touching the guest.
2. `guest-plan --scenario S2` proposes `stat /etc/sudoers`, `ls -ld /etc/sudoers.d`,
   `stat /usr/bin/sudo`.
3. `stat /etc/sudoers` showing a mode wider than `0440` is a strong candidate: sudo ignores a
   sudoers file it considers unsafe. `stat /usr/bin/sudo` without setuid belongs to S3.
4. Whether the account is listed in sudoers or in the sudo/wheel group is a **content** question
   outside the whitelist - ask the customer for the output, then give the membership change as a
   manual step after a snapshot.

### S3 setuid, mode or owner damaged on a privilege binary

1. `guest-plan --scenario S3` proposes `stat` on `/usr/bin/sudo`, `/usr/bin/su`,
   `/usr/bin/passwd`, plus `findmnt -o OPTIONS,TARGET`.
2. The mount check comes before the file conclusion: `nosuid` on `/` or `/usr` produces the same
   refusal with a perfectly good file, and `ro` blocks an in-place repair.
3. Compare against `perm-baseline.md`, stating its UNVERIFIED status. A missing setuid bit plus a
   recent `chmod -R`, `chown -R` or a restore over `/usr` is a coherent story; a missing bit with no
   change history should prompt a package integrity check, which the customer runs manually.

### S4 business file or directory wrong owner or mode

1. Ask for the absolute path **and** the expected owner, group and mode. The skill never guesses
   business intent.
2. `guest-plan --path <absolute path>` proposes `stat <path>` and `ls -l <path>`.
3. Report the four columns from `perm-baseline.md`. A deep tree check (`find -perm`) is outside the
   whitelist and goes to the customer as a command.

## Step 4 - when the guest channel is unavailable

Cloud Assistant not ready, `RunCommand` refused, `NoPermission`/`ImplicitDeny` returned, or the
customer declines approval: `STATUS: DEGRADED`, name the missing step, and give the same whitelisted
command for the customer to run and paste. The diagnosis does not stop, only its automation does.

## Step 5 - manual repair guidance, and the backup first

Every repair is the customer's action. Before any of them, offer `snapshot --disk-id <DiskId>` so a
rollback point exists; that call is mutating and needs its own approval.

* Snapshot the system disk **before** changing modes, owners, sudoers or sshd configuration.
* Keep a working session open while editing sshd configuration, so a bad edit can be reverted from
  the session that still works.
* Change one path at a time, from the narrowest scope, and re-test after each change rather than
  recursing over a tree.
* Reinstalling a package or restoring a binary is a repair with its own risk: hand it over with the
  distro's documented procedure and the snapshot already taken.
* Recovery paths that need the instance offline - single-user mode, an attached repair disk, VNC -
  are console or lifecycle operations and are outside this skill entirely.
* **Lost credential**: reset from the console credential page. No credential-reset API was verified
  for this tier, so the skill gives the console path and nothing else.

## Documentation verified for this tier

Only these links were confirmed by the evidence supplied for this tier; quote them as-is and do not
add others from memory.

* Instance logon credential management (manual credential reset path) -
  https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management.md
* Guidance on avoiding direct root logon to an instance -
  https://help.aliyun.com/zh/ecs/user-guide/avoid-logging-in-to-the-instance-as-root.md
* RAM policy that prohibits root as the initial user of a Linux instance -
  https://help.aliyun.com/zh/ecs/user-guide/prohibit-ram-users-from-creating-linux-instances-with-root-as-initial-user.md
* Letting a RAM user run Cloud Assistant commands -
  https://help.aliyun.com/zh/ecs/user-guide/run-cloud-assistant-commands-as-a-regular-user.md
* ECS security announcements (point here if a privilege-escalation advisory could apply to the
  customer's component version; no specific advisory was supplied for this tier, so do not name one) -
  https://help.aliyun.com/zh/ecs/security-announcement.md

**Documented gap**: official pages for sudoers syntax, setuid repair, VNC rescue logon and
single-user mode recovery were **not** returned by the documentation search run for this tier. They
are a known hole; state it as a gap and hand the customer to their distribution's own
documentation rather than inventing a link.

## Known gaps carried into every report

* Zero tickets supplied: scenario ranking, root-cause distribution and the error strings customers
  actually paste are unmeasured. Quote the customer's own error line instead of a presumed one.
* Expected mode values are UNVERIFIED per `perm-baseline.md`.
* Windows is out of scope: the batch decision was to include it only if Windows tickets appeared,
  and none were supplied.
* The capacity area (`df`, `du`, `lsof`, inode) was deliberately left out; the slug of that skill was
  not injected for this tier, so name it from the current skill list when handing off.
