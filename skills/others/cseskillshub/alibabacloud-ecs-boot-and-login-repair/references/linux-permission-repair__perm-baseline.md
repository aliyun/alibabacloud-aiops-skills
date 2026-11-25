# Expected mode and owner per checked path

> **Baseline status: UNVERIFIED for this tier.**
> No representative ticket, image inspection or package manifest was supplied as evidence for this
> tier, so the values below are the ordinary expectations for a Linux distribution, **not** measured
> readings from the customer's image. Before presenting any line as a fact to a customer, compare it
> against a known-good instance of the **same image** in the same account, or against that image's
> package metadata. The same table is embedded as `PERMISSION_BASELINE` in
> `scripts/axes/linux_permission_repair/_constants.py`, and `guide` prints this status line with it.

A mismatch is a **candidate** root cause, never a conclusion. The conclusion needs the observed
`stat` output from the customer's instance next to the reading from a known-good instance.

## Privilege binaries

| Path | Expected | Why it matters when wrong |
|---|---|---|
| `/usr/bin/sudo` | mode `4755`, setuid bit present, owner root, group root | without setuid, sudo cannot become uid 0 and reports an effective-uid problem |
| `/usr/bin/su` | mode `4755`, setuid bit present, owner root, group root | without setuid, `su` cannot switch identity for a normal user |
| `/usr/bin/passwd` | mode `4755`, setuid bit present, owner root, group root | without setuid, a normal user cannot change their own password |

Some images ship these under `/bin` as a symlink to `/usr/bin`; `stat` on the symlink path shows the
link, `stat -L` shows the target, and the target is the one that needs the bit.

## Authorization files

| Path | Expected | Why it matters when wrong |
|---|---|---|
| `/etc/sudoers` | mode `0440`, owner root, group root | sudo refuses to load a sudoers file that is group- or world-writable |
| `/etc/sudoers.d` | directory, mode `0750` or `0755`, owner root, group root | drop-in files are parsed only while the directory itself is safe |
| `/etc/passwd` | mode `0644`, owner root, group root | group-writable here breaks every logon path, not only sudo |
| `/etc/shadow` | mode `0640` or `0000`, owner root, group root or `shadow` depending on the image | wrong group here stops password authentication for all users |

`/etc/sudoers.d` also requires the individual drop-in files to be root-owned and `0440`; a file
whose name contains `~` or a `.` is silently ignored by sudo. Naming and content are only visible
through a content-reading command, which is outside the whitelist
(`guest-diag-whitelist.md`), so ask the customer for the output.

## Home and temporary directories

| Path | Expected | Why it matters when wrong |
|---|---|---|
| `/root` | mode `0700`, owner root, group root | wrong ownership stops root using its own profile and key file |
| `/tmp` | mode `1777` sticky, owner root, group root | sudo and other privilege helpers need a writable, sticky `/tmp` |

## Mount options that override all of the above

`findmnt -o OPTIONS,TARGET` is the check. If the filesystem holding `/usr` or `/` is mounted with
`nosuid`, the setuid bit is present and ignored; with `ro`, a repair attempted in place will fail.
Report the mount option as the finding, not the file, because fixing the file cannot work while the
mount says otherwise. Container-rooted or bind-mounted paths are the common place this shows up.

## How to use this table in a report

Four columns, one row per checked path: **path**, **observed** (verbatim `stat` output plus the
command that produced it), **expected** (from this table, with its UNVERIFIED status), **difference**
(your reading). If a row has no observed value, say which approval or which availability gap is
missing rather than leaving it implied.
