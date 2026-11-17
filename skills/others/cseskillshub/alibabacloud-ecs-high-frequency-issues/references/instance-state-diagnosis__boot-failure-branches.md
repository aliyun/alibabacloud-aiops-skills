# Boot and start failure branches

Routing table for "the instance will not come up". Every signal below is text the customer
(or an operator looking at the console) quotes; this skill never obtains a boot screen by
API, so the left column is always customer-provided.

| Branch | Quoted signal | Layer | Verdict | Manual guidance |
|---|---|---|---|---|
| `nostock` | `OperationDenied.NoStock` | resource availability, cloud side | the instance type is sold out in that zone, so a start is refused; capacity, not a fault | change to an in-stock type in the same region, move zone/region, or retry later; if the goal is data extraction before release, take a custom image or snapshots first |
| `grub_rescue` | VNC shows `grub >`; `ls` reports `unknown filesystem` on partitions | bootloader | boot chain damaged after an update or change; the OS is never reached, so every remote method fails as a symptom | capture the VNC screen (four checks below); repair boot manually **after** a snapshot, or let the customer roll back a snapshot of the system disk |
| `custom_image` | an instance built from a custom/imported image never boots | image compliance | images must be cloud-ready: prepared per the import guide, and no interactive installer stage; an image that still needs an OS install can never come up | re-make the image per the import guide; the six-step path used in tickets is a temporary pay-as-you-go data disk, install onto it, snapshot it, build an image from that snapshot, then swap it -- each disk choice is irreversible if wrong, so state that before the customer acts |
| `fstab_emergency` | boot drops to emergency/recovery; `Timed out waiting for device`; a `fstab` entry pointing at a device that is gone | auto-mount, guest boot stage | a stale auto-mount entry blocks normal boot; the instance looks stuck or lands in a recovery shell | manually comment the offending `fstab` line (customer edit) or attach a repair disk; snapshot first; afterwards configure the correct auto-mount |
| `disk_full_boot` | `No space left on device`, exhausted inodes, guest up but network/services never initialize | capacity blocking boot | a full system disk (or full inode table) can break boot-time initialization, which looks like "the server will not start" | snapshot, then the customer frees space or expands the disk; the cleanup itself is the capacity tier, layer judgement only |
| `atkbd_noise` | `atkbd serio0: Unknown key pressed` | harmless log line | virtual-keyboard compatibility warning during reboot; generally does not block boot | do not treat as the cause; continue with the VNC four checks |
| `bios_boot_order` | the customer entered BIOS / changed boot order, "select the system" | boot entry | the instance boots the wrong or no device | ask whether any boot-order change was made; restore the default boot path from the console VNC session |
| `expiry_stop` | `Stopped` + financial lock, "renew", "expired" | account lifecycle | the platform stopped it on expiry; a start stays blocked until renewal | renew in the billing console; if renewal cannot happen now, build a custom image to preserve the environment |
| `intrusion` | tampered `/etc/passwd`, miner or ransomware behaviour, destroyed Cloud Assistant agent | security incident | boot and recovery failures are downstream of the incident; diagnosis must not tidy up an incident scene | snapshot all disks immediately (evidence and rollback), then engage security response; restoring the agent can require a system-disk re-initialization, which is destructive and customer-executed |

## VNC four checks (the only way to place a boot-stage failure)

Ask the customer to open console VNC and report which of these the boot screen shows:

1. frozen at the GRUB menu;
2. `fsck` running for a long time or reporting errors;
3. `Emergency mode` / a dracut rescue prompt;
4. kernel panic output.

Anything else -- a login prompt, a systemd line that keeps scrolling, a blank cursor after
"Operating System not found" -- is also information; ask for the exact last line. No cloud
API returns this screen, so this observation is inherently human.

## Log lines that look like causes but are not

- `atkbd serio0: Unknown key pressed` (row above).
- A `404 Not Found` page: the web server answered, so the service is running; `404` is not
  "service failed to start".
- Port 80 answering while 443 times out: a certificate or HTTPS listener question, not an
  instance-state question.
- After a snapshot rollback, application processes stay down unless autostart was
  configured: "the program is stopped after rollback" is a guest service fact, not a boot
  failure.
- `ErrCode:-401, ErrMsg:Client not connected, current status:STARTING`: an application
  client state string, not an ECS instance state -- out of this tier.

## What this skill must not claim

- It cannot fetch a boot screen, so it never names a boot stage without a VNC observation.
- It cannot detect virtio/cloud-init presence in an image through a public query; image
  compliance stays a guided check against the import document.
- It cannot produce the error code of a failed start: the start is a customer action, so the
  code comes from the customer's console message or request id.
- It never performs the start, the force stop, the rollback, the re-initialization or the
  file edit itself.

## Documents

- Import a custom image: `https://help.aliyun.com/zh/ecs/user-guide/import-an-image`
- Create a custom image from an instance: `https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance`
- Share a custom image: `https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image`
- Roll back a disk with a snapshot: `https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot`
- Re-initialize a system disk: `https://help.aliyun.com/zh/ecs/user-guide/re-initialize-a-system-disk`
- Renew a subscription instance: `https://help.aliyun.com/zh/ecs/manually-renew-an-instance-1`
- Workbench system management (in-guest entry point):
  `https://help.aliyun.com/zh/ecs/user-guide/workbench-system-management.md`
- Stop or uninstall the Cloud Assistant agent:
  `https://help.aliyun.com/zh/ecs/user-guide/stop-and-uninstall-the-cloud-assistant-agent`
