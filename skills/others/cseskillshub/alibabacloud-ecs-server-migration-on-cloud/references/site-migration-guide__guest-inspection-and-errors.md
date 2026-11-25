# In-guest inspection and recognised errors

Instance-level facts that cloud queries do not return: the volume of a site, what the guest actually
recognises as disk size, whether a directory survived the copy, whether a deleted-but-open file is
still holding space.

## Protocol

1. Name the fact you need, then pick exactly one command from the allow-list below.
2. Vet the exact string: `python3 scripts/axes/site_migration_guide/site_migration.py guest-commands --check "<command>"`.
3. Announce before anyone runs it: what the command reads, which paths it touches, that it produces
   no change, and that the confirmation covers only this one command.
4. The customer or their technician runs it and pastes the raw output. Record it as
   customer-provided evidence; never restate a number that did not appear in the paste.
5. No channel and no paste: continue with cloud evidence and end the report `STATUS: DEGRADED`,
   naming the missing fact.

## Allow-list

| Operating system | Command | What it reads |
|---|---|---|
| Linux | `df -h` | File systems, size and usage as the guest sees them, including the recognised system-disk size and what is mounted |
| Linux | `df -i` | inode totals and free inodes per file system |
| Linux | `du -x --max-depth=1 <path>` | Size of each first-level entry under one path, staying inside one file system |
| Linux | `du -sh --inodes <path>/*` | Size and inode count per entry directly under one path |
| Linux | `findmnt` | Mount table: device, mount point, file system type |
| Linux | `stat <path>` | Metadata of one file or directory: size, timestamps, link count |
| Linux | `ls -l <path>` | Directory listing with sizes and timestamps |
| Linux | `wc -l <file>` | Line count of one text file, a quick completeness check |
| Linux | `lsof +L1` | Open files with no directory link: space held by deleted-but-open files |
| Windows | `Get-Volume` | Per-volume size and free space as Windows sees it |
| Windows | `Get-PSDrive` | Used and free space per drive letter |
| Windows | `Get-ChildItem <path> -File` | File listing of one directory with sizes |
| Windows | `fsutil volume diskfree <driveLetter>:` | Total, free, and available bytes of one volume |

## Outside the allow-list for this build

Service and socket inspection such as `systemctl status <service>`, `ss -lnt`, `netstat -ano`,
`Get-Service`, `Get-Process`, and `ipconfig /all` are not offered as commands to run by this skill;
ask the customer to run them and paste the output, and say which conclusion depends on it.

Anything that deletes, empties, truncates, redirects into a file, moves, copies, formats, partitions,
rebuilds a file system, changes a mount, tunes a file system, kills a process, or restarts a service
or instance is refused for automation. The answer becomes the documented console or in-instance
procedure, its risk, and the snapshot-first gate. `lsof +L1` is on the allow-list as an inspection
command; acting on what it reports (deleting the file, restarting the service) is not.

## Windows caveats

- NTFS has no inode counter, so a "too many files" diagnosis available on Linux via `df -i` has no
  direct equivalent. Mark a Windows file-count estimate as lower confidence and name the missing
  measurement.
- Deep trees with many small files make built-in compression appear to hang. That is throughput, not
  corruption: archive per directory in batches or use a faster archiver, and confirm archive sizes
  before transferring.

## Recognised error strings

Match what the customer pasted, then act on the meaning. These strings come from customer reports, so
treat a near miss as a question rather than a conclusion.

| Fragment in the pasted text | Meaning | Next action |
|---|---|---|
| `Error establishing a database connection` | The moved application still points at the old database host, user, password, or name | Confirm reachability from the destination, then have the customer update the application configuration and reload the site |
| `OthersLinux_64` or `OthersLinux_32` | An imported source that was not recognised as a mainstream distribution; the console cannot reset the root password for that image type | Snapshot first, then change the password from inside the instance over the console connection or attach an SSH key pair |
| a missing `pid file` report from a web server | The service is not actually running, or a reload or check command was used where a start was needed | The customer starts the service with their own service manager and then verifies the listening port; service control is not performed by this skill |
| blank page or missing theme right after a move | Program files are incomplete rather than misconfigured | Compare the theme, template, and upload directories against the pre-check baseline |
| site reachable by address but not by name | DNS record still resolves to the old server, or the local resolver cached it | Set the record value to the destination public address, clear the local cache, retest externally |
| `NoPermission` or `ImplicitDeny` | One inspection action is not granted to the credential in use | Print the failing action and its statement from [ram-policies.md](ram-policies.md); continue and report `STATUS: DEGRADED` |

A stale static private address copied along with the disk image, a security group without the login
port, and a service that never started all look identical from the outside: a failed login. Distinguish
them with the bound group ids from the cloud evidence, the guest mount and interface facts from a
pasted command, and the service state from the customer.
