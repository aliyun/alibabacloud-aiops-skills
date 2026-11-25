# Documentation index, with provenance

Two classes, labelled honestly. **Verified** means the article was located through the documentation search
used while preparing this skill. **Quoted from support practice** means the link appeared in the material
reviewed for this tier, i.e. a support engineer pointed a customer at it; it is real but was not
independently re-checked, so treat the destination as needing confirmation before quoting it to a customer
in a durable document.

Never cite an article that is not in this file. If a needed topic is missing, say the topic is missing from
this skill's verified sources rather than guessing a title or a link.

## Verified — boot, disk, and rescue

| Topic | Article |
|---|---|
| Building a disk from a snapshot (the core data-rescue step) | https://help.aliyun.com/zh/ecs/user-guide/create-a-disk-from-a-snapshot.md |
| Data disk initialization overview | https://help.aliyun.com/zh/ecs/user-guide/overview-27.md |
| Re-initializing a data disk (manual action, cited not executed) | https://help.aliyun.com/zh/ecs/user-guide/re-initialize-a-data-disk.md |
| The shared responsibility model, i.e. why in-guest updates and boot configuration are the customer's side | https://help.aliyun.com/zh/ecs/user-guide/ecs-shared-responsibility-model.md |
| Fixing high-severity vulnerabilities (belongs to the patch skill; cited to define the boundary) | https://help.aliyun.com/zh/ecs/user-guide/fix-high-risk-security-vulnerabilities.md |
| Using a skill to scan or install system patches (the boundary article for `alibabacloud-ecs-patch-management`) | https://help.aliyun.com/zh/ecs/user-guide/use-skill-to-scan-or-install-system-patches.md |
| The multi-terminal console session feature, i.e. the in-guest channel this skill guides but does not drive | https://help.aliyun.com/zh/ecs/user-guide/use-the-multi-terminal-feature.md |
| Known issues of public images, including out-of-support releases | https://help.aliyun.com/zh/ecs/known-issues-of-public-images.md |

Also verified as a topic, but recorded with an incomplete address during preparation, so the link is not
reproduced here: the article on initializing a Linux data disk of up to two tebibytes, covering GUID versus
master-boot-record selection and the filesystem choice with the boot-time mount entry. Locate it from the
data disk initialization overview above rather than from memory.

## Quoted from support practice — confirm before use

| Topic | Address seen in the reviewed material |
|---|---|
| The fstab mount-point and startup integrity-check error article, which is what the console diagnosis advice refers to for this branch | https://help.aliyun.com/document_detail/450291.html |
| Booting a Linux or FreeBSD-like instance into single-user mode | https://help.aliyun.com/zh/ecs/user-guide/boot-a-linux-or-freebsd-like-ecs-instance-into-single-user-mode |
| Enabling kernel dumps on a Windows instance, so the next crash is diagnosable | https://help.aliyun.com/document_detail/41013.html |
| Enabling or disabling kernel upgrades through the package manager on a Linux instance | https://help.aliyun.com/zh/ecs/support/enable-or-disable-the-package-manager-for-kernel-upgrades-on-a-linux-instance |
| Configuring a swap area on a Linux instance | https://help.aliyun.com/zh/ecs/support/how-do-i-configure-the-swap-partition-of-a-linux-instance |
| Sharing a snapshot with another account (used in the dump-export path) | https://help.aliyun.com/zh/ecs/user-guide/share-a-snapshot |
| Exporting a custom image to local storage | https://help.aliyun.com/zh/ecs/user-guide/export-a-custom-image |
| Instance logon credential management, including the offline reset that needs a stop | https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management |
| Re-initializing a system disk (manual, destructive to the system volume) | https://help.aliyun.com/zh/ecs/user-guide/re-initialize-a-system-disk |
| Creating a snapshot | https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot |

Numeric article identifiers of the same topics also appeared in the reviewed material in the form
`https://help.aliyun.com/document_detail/<id>.html` for snapshot creation, snapshot cost, snapshot deletion,
building a disk from a snapshot, attaching a disk, re-initializing a system disk, rolling back a snapshot,
replacing the system disk, and creating or sharing a custom image. Those identifiers were recorded from
support replies rather than from the documentation service, so the equivalent titles above are the safe
citation and the numeric addresses should be confirmed one by one before being published to a customer.

## Third-party sources

Vendor security advisories are the authority for a specific vulnerability, and Microsoft's update catalog is
where a specific knowledge-base article is downloaded by hand. Both appeared in the reviewed material:

- A remote-desktop service vulnerability advisory used to explain repeated crashes on an out-of-support
  release: https://msrc.microsoft.com/update-guide/en-US/vulnerability/CVE-2019-0708
- The Microsoft update catalog search form for a named knowledge-base article, used when the update service
  itself could not deliver it.

Cite these only when the customer's own evidence names the vulnerability or the knowledge-base article.

## Topics with no source in this skill

Deliberately unresearched, and therefore absent from the guidance files rather than filled in from memory:
rebuilding a GRUB installation and its EFI entries step by step; mounting and using the console repair
environment, including its exact console path; rebuilding a Windows boot manager and boot configuration data
store; handling a volume remounted read-only after recorded errors; diagnosing Linux emergency mode from the
systemd unit that failed; the compatibility matrix between an image, its default kernel, and host security
agents; and the expected duration of a first boot after a Windows feature update.

Where the workflow needs one of these, the skill states the gap and points at the console capability in
generic terms, as with the repair-environment entry, which is described as a console diagnostic and repair
capability without a menu path. Adding a path from memory is exactly the failure mode this file exists to
prevent.
