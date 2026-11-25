# Read-Only Self-Checks for the Customer to Run and Paste Back

This skill has **no access inside the customer's instances** and never runs commands there. When a
conclusion depends on guest-side state, the answer is produced by the customer: they run a read-only
check in their own session, paste the **output text**, and this skill interprets it or routes it to
the domain that owns the fix.

Rules that apply to every item below:

- Only listing and status commands. Nothing here changes data, configuration or files, and nothing
  here is executed by this skill.
- Paste the output only. **Never paste** a panel or server address, a username, a password, a
  private key, a token, a cookie, or a two-factor code. Resource ids (instance, disk, snapshot) are
  safe and useful.
- This build covers Linux guests only; there is no verified Windows equivalent for these checks.

## 1. Which disk is which inside the system

Use when a customer is unsure which device is the cloud disk, which is local, or where a restored
file system is mounted.

| Check | Command the customer runs | What it proves |
|---|---|---|
| Block devices and mounts | `lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT` | device names, sizes and mount points; matches the disk sizes from the read-only inventory |
| Mounted file systems | `findmnt -t ext4,xfs` | which device backs which directory |
| Space and inode usage | `df -hT` and `df -i` | used / free space and whether the inode table is exhausted |
| Ownership of a restored directory | `ls -l <directory>` and `stat <file>` | presence, size, owner and timestamps of the copied files |

Cross-check with the cloud side: `python3 scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py --region-id <region>` reports
each disk's id, category, size, zone and status. If a disk is `In use` and attached on the cloud side
but missing in `lsblk`, the mismatch is the fact to carry into the next step (and it is an
instance-side question, not a replication question).

## 2. Website or panel symptoms after copying data back from a disk

Typical wording: "the HTML pages return 404, the PHP pages render blank, the images work, the files
are there and the permissions look normal".

Checks the customer can read back:

| Check | How the customer reads it | What it proves |
|---|---|---|
| Index file name and location | `ls -l <site root>` | whether the entry file exists with the exact name the server is configured to serve |
| Entry file content is real | `stat index.html` plus `head -n 5 index.html` | non-zero size and readable content |
| Panel file protection | open the control panel's site settings and read whether the tamper-proof / file-protection switch is **on** | a protection feature blocks reads, writes and renames of site files, which produces exactly this symptom |
| Served path and default document | read the site's root directory and index-file settings in the panel or web-server site configuration | whether the request maps to the directory the files were copied into |

What this skill then says: a protection switch and a site-root mapping are panel and web-server
configuration, i.e. the panel / website operations domain. In the verified ticket of this tier the
customer found the cause themselves (the panel's tamper-proof feature) and resolved it themselves.
This skill does not change the switch, does not ask for panel access, and does not promise a
diagnosis it cannot see.

## 3. Slow copy between a cloud disk and a local disk

Checks the customer can read back:

| Check | Command the customer runs | What it proves |
|---|---|---|
| Device class and rotation model | `lsblk -d -o NAME,SIZE,ROTA,TYPE` | local disks and virtual devices differ from SSD-backed cloud disks in small-file workloads |
| Live IO pressure | `iostat -x 1 5` (needs the sysstat package installed) | utilisation, wait time and throughput per device during the copy |
| Small-file volume | `find <directory> -type f \| wc -l` and `du -sh <directory>` | many small files, which is the usual driver of a slow cloud-to-local copy |
| Filesystem and mount options | `findmnt <mountpoint>` | sync or async write behaviour that throttles throughput |

Cloud-side facts come from the inventory: disk `category`, `size_gib`, `status` and
`disk_charge_type`.

Honest boundary: an overdue account causing disk IO throttling was only an **unverified hypothesis**
in the source ticket of this tier; this skill states it that way and never asserts it as a cause.
Throughput testing and the verdict belong to the disk performance domain.

## 4. Console-side readings (what the customer looks up and reports)

| Question | Where the customer looks | What to paste back |
|---|---|---|
| Is a replication pair running, and in what state? | EBS console > Enterprise-level Features > async replication page, in the region of the pair | pair id, primary and secondary disk ids with their regions and zones, status, RTC setting |
| Which regions hold my resources? | region selector of each console page | the region names actually shown |
| Do snapshots exist, and where? | ECS console > Snapshots, per region | snapshot ids, region, creation time, source disk |
| Automatic snapshot policies on a disk | ECS console > Disks > the disk's automatic snapshot attributes | policy id or "none" |
| What is my account balance / is it overdue? | the billing console, Balance and Orders pages, by the customer | only the fact needed ("balance positive / overdue"), never invoice attachments |

Replication-pair state is the one item this skill cannot read at all: the pair objects are outside its
read-only API surface, so the console page above is the authority and the customer's reading of it is
the evidence.

## 5. Turning a pasted output into a conclusion

1. Quote the exact line or field you are relying on; do not paraphrase a number.
2. Name the source: "customer-provided `lsblk` output" versus "read-only inventory for region
   `cn-hangzhou`" versus "official document".
3. If the output does not settle the question, say so and hand off with the wording in
   `references/disk-replication-dr-guide__handoff-map.md`. Never extend a partial signal into a verdict.
