# M1: ossfs Mount Failure Attribution Knowledge

Knowledge base for ossfs / FUSE mount failure attribution. Every fact below
is grounded in the official documentation (sources listed per section) or in
measured ticket patterns. This skill only DIAGNOSES and ADVISES - it never
executes any mount command.

## Sources (official documentation, verified)

| Topic | Official doc |
|---|---|
| ossfs quick start (2.0 config, credential env vars, endpoint choice) | https://help.aliyun.com/zh/oss/user-guide/ossfs-quick-start |
| ossfs FAQ (error messages and solutions) | https://help.aliyun.com/zh/oss/developer-reference/ossfs-faq |
| ossfs 1.0 configuration | https://help.aliyun.com/zh/oss/developer-reference/configurations-for-ossfs-1-0 |
| ossfs mount options | https://help.aliyun.com/zh/oss/developer-reference/common-options |
| ossfs 2.0 FAQ (mount/read/write error attribution) | https://help.aliyun.com/zh/oss/developer-reference/ossfs-2-0-faq |
| ossfs 1.0 common mount errors (credential/region/V4) | https://help.aliyun.com/zh/oss/analysis-of-common-mount-error-causes-of-ossfs |
| ossfs PrivateLink private-network mounting | https://help.aliyun.com/zh/oss/developer-reference/private-network-mounting-through-privatelink |
| ossfs large-file copy Input/output error | https://help.aliyun.com/zh/oss/the-input-or-output-error-error-message-is-returned-when-you-try-to-copy-data-by-using-ossfs |
| ossfs non-root user mounting | https://help.aliyun.com/zh/oss/how-ossfs-mounts-a-bucket-to-an-ecs-instance-by-using-a-non-root-user |
| "The bucket you access does not belong to you" = client-side pre-check permission (STS grants temporary permissions to OSS) | https://help.aliyun.com/zh/oss/the-access-denied-by-authorizer-s-policy-error-message-is-returned-when-sts-grants-temporary-permissions-to-oss |

## Pre-mount checklist (the five canonical root causes)

### 1. Credential file / credential chain

- ossfs 1.0: credential file `/etc/passwd-ossfs`, line format
  `<bucket>:<AccessKeyId>:<AccessKeySecret>`; the file permission MUST be
  restricted - ossfs refuses to start with
  `credentials file /etc/passwd-ossfs should not have others permissions`
  when others can read it; fix with `chmod 640 /etc/passwd-ossfs`
  (ossfs FAQ, permission / mount sections).
- ossfs 2.0: credentials come from the environment variables
  `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET`; an unset pair surfaces as
  `empty credential` at mount time (ossfs quick start).
- Classic measured root cause: the AccessKey belongs to a DIFFERENT account
  than the bucket owner, or the AccessKey was rotated/deleted after the
  mount - the mount then fails with 403 or the mounted directory stops
  responding. Verify the credential's account UID against the bucket owner
  UID (the entry script's GetCallerIdentity + GetBucketInfo owner_id pair
  provides this evidence).
- Never ask the user to paste AK/SK into the conversation; guide them to
  fix the credential file / environment on their own host.

### 2. Endpoint

- The mount endpoint's region MUST equal the bucket location, otherwise OSS
  returns `The bucket you are attempting to access must be addressed using
  the specified endpoint` (ossfs FAQ). The entry script matches the user's
  `--endpoint` against the GetBucketInfo `location` automatically.
- Same-region mount hosts on Alibaba Cloud (ECS / ACK / ACS nodes) should
  use the internal endpoint `oss-<region>-internal.aliyuncs.com`; the
  official quick start explicitly discourages mounting through the public
  endpoint (high latency / unstable Internet produces stalls).
- Internal endpoints resolve only inside the Alibaba Cloud network of that
  region; a mount host outside the cloud fails DNS.
- ossfs does NOT support custom domains.

### 3. Permission (RAM)

- The mount credential needs at least `oss:ListObjects` on the bucket plus
  `oss:GetObject` / `oss:PutObject` for the operations actually used; a 403
  during mount usually means the credential lacks these or the bucket
  belongs to another account.
- `The bucket you access does not belong to you` during mount is **first** a
  client-side pre-check permission failure, NOT a bucket-ownership problem.
  Per the official doc, ossfs / ossutil / SDK call `ListObjects` (and some
  tools also `GetBucketInfo`) before the real operation to validate bucket
  access; if the mount credential's policy grants only object-level actions
  (`oss:GetObject` / `oss:PutObject` on `acs:oss:*:*:<bucket>/*`) it lacks
  `oss:ListObjects` on the bucket-level resource, so the pre-check returns
  HTTP 403 with this message. Official wording (translated from the Chinese
  doc): "This error occurs during the client-side pre-check phase and does
  NOT indicate a bucket-ownership anomaly". Typical signature: calling PutObject
  directly succeeds while the client tool fails. Fix: grant `oss:ListObjects`
  on the bucket-level resource `acs:oss:*:*:<bucket>` (official example uses
  the wildcard `acs:oss:*:*:*`, replace the last `*` with the bucket name),
  and - if the tool pre-checks it - grant `oss:GetBucketInfo` independently;
  `oss:PutObject` stays at object level `acs:oss:*:*:<bucket>/*`. **Secondary**
  hypotheses only: wrong-account credential or wrong-region endpoint (see M2
  for the container-side authorization-model confusion).

### 4. FUSE dependency

- ossfs is a FUSE (userspace) filesystem; the host needs the FUSE kernel
  module and matching libfuse. `fuse: device not found, try 'modprobe fuse'`
  inside a container means the container lacks FUSE access - the official
  guidance is running the container with elevated privileges
  (`docker run --privileged=true ...`) or providing `/dev/fuse` (ossfs FAQ).
- `ossfs: error while loading shared libraries: libcrypto.so.1.1 ...` =
  installation package / OS mismatch - install the package matching the OS.
- ossfs only supports Linux (CentOS/Rocky/Alibaba Cloud Linux/Ubuntu/
  Debian per the official support matrix); Windows has no ossfs support -
  use Cloud Storage Gateway or Rclone there.

### 5. Mountpoint

- The mountpoint directory must exist and be empty:
  `unable to access MOUNTPOINT ...: Transport endpoint is not connected`
  when the directory was not created; `Mountpoint directory ... is not
  empty` when it contains files (manual options: create the directory /
  mount elsewhere or add `-ononempty` - guidance only, user executes).

## Mount directory disappeared / process exited

Symptom: the mountpoint suddenly becomes inaccessible, `ls` returns
`Transport endpoint is not connected`, `df` no longer shows the mount, or a
same-name directory cannot be re-created.

Attribution (all documented or measured):

1. **The ossfs process exited while the kernel mount entry remains.** The
   stale entry must be cleaned with `fusermount -u <mountpoint>` before
   remounting (guidance only). Typical exit causes:
   - **OOM kill**: large directories blow up memory in ListObjects/stat -
     the official FAQ records `Out of memory: Kill process ... (ossfs)`;
     mitigation guidance: raise `-omax_stat_cache_size`, or switch
     high-concurrency workloads to ossutil / ossfs 2.0.
   - **Credential rotation/deletion**: the AccessKey backing the mount was
     deleted; the mount stops answering reads/writes.
2. **The mountpoint directory itself was removed or is occupied by a stale
   entry** - same-name directory creation fails until the stale mount is
   cleaned.
3. ossfs is NOT atomic and not designed for IO-intensive or
   reliability-critical workloads; recurring disconnects are expected under
   heavy scan/write load. (Experiential positioning - no verbatim official
   source could be located across search / index-grep / WebSearch; treat as
   guidance, not an official quote.)

Evidence collection guidance for the user (manual, they execute):
`-o dbglevel=dbg -d` debug log (CentOS: `/var/log/messages`, Ubuntu:
`/var/log/syslog`), `dmesg | grep -i oom`, `ps aux | grep ossfs`.

> **dbglevel value dual-caliber** (verified 2026-09-03): the ossfs FAQ uses
> `-odbglevel=dbg`, while the common-options parameter table lists the legal
> levels as `critical` / `error` (default) / `warn` / `info` / `debug`. Both
> spellings appear in official docs; on strictly-parsing builds `dbg` may be
> rejected, so if the debug log stays empty, retry with `-odbglevel=debug`.

## Error-message routing table

| Error message (verbatim from ossfs) | Category | First attribution |
|---|---|---|
| `must be addressed using the specified endpoint` | endpoint_mismatch | endpoint region != bucket location, OR credential UID != bucket owner |
| `The bucket you access does not belong to you` | preflight_permission | client-side pre-check (`ListObjects` / `GetBucketInfo`) denied by an object-prefix-only policy - per official doc this does NOT indicate a bucket-ownership problem; grant `oss:ListObjects` on `acs:oss:*:*:<bucket>` (bucket level) and `oss:GetBucketInfo` if the tool pre-checks it. Ownership / wrong-region remain secondary hypotheses only. |
| `Transport endpoint is not connected` | transport_disconnected | ossfs process exited / mountpoint missing |
| `credentials file /etc/passwd-ossfs should not have others permissions` | creds_file_perm | file mode too open; `chmod 640` |
| `--oss_bucket/--oss_endpoint must be set on the commandline` | conf_syntax | ossfs2.conf keys missing the `--` prefix |
| `empty credential` | empty_credential | OSS_ACCESS_KEY_ID/SECRET env vars unset (ossfs 2.0) |
| `fuse: device not found, try 'modprobe fuse'` | fuse_missing | container lacks FUSE access |
| `Mountpoint directory ... is not empty` | mountpoint_not_empty | mount onto an empty directory (or `-ononempty`) |
| HTTP 403 on read/touch of an object | permission_403 / archive | RAM permission gap, OR unrestored Archive object (see M3) |
| `unexpected error from stat(/etc/passwd-ossfs): No such file or directory` | creds_file_missing | ossfs 1.0 credential file not created |
| `Invalid signing region in Authorization header` | v4_region_mismatch | `-oregion` does not match the bucket region when using V4 signing |
| `Could not determine how to establish security credentials` | creds_unresolved | none of passwd-ossfs / ram_role / env vars yields valid credentials |
| V1-signature deprecation NOTICE at mount | v1_deprecation | ossfs >= 1.91.4 supports V4: add `-osigv4 -oregion=<region>` (guidance) |
| mount timeout (`readwrite_timeout`; dual-caliber default: 60s per ossfs-faq vs 120s per common-options - verified 2026-09-03) | mount_timeout | raise `-oreadwrite_timeout` for slow links (guidance) |
| `fusermount: failed to open current directory: Permission denied` | fuse_cwd_perm | fuse bug: run the mount command from a directory the user can read |
| `operation not permitted` on `ls` inside a working mount | invisible_name | bucket contains objects whose names carry invisible characters; rename them via another tool |
| `There is no enough disk space for used as cache(or temporary) directory` | tmp_space | free space on /tmp < `multipart_size * parallel_count`; shrink `multipart_size` or free space (guidance) |
| `Input/Output error` copying large files | io_error_bigfile | high disk load from large-part copying; lower `parallel_count` / `multipart_size`, or use ossutil multipart instead |
| `NSS error -8023` (CentOS 7.x HTTPS mount, ossfs >= 1.91.5; also `ls` Input/Output error) | nss_old | outdated NSS library; `yum update nss` then remount (guidance) |
| ram_role mount fails on ossfs >= 1.91.7 | imdsv2 | check `curl http://100.100.100.200/latest/meta-data/ram/security-credentials/<role>`; if reachable, add `-o disable_imdsv2` (guidance) |
| uploaded files all get Content-Type `application/octet-stream` | mime_missing | `/etc/mime.types` absent; install `mime-support`/`mailcap` or add the file, then remount |
| a folder object shows up as a plain file | folder_misrec | folder object has non-zero size or wrong Content-Type; mount with `-ocomplement_stat` or fix/remove the object via ossutil |

Note: a 403 on `touch`/read of a single file inside an otherwise working
mount is typically the ARCHIVE case (unrestored archive object), not a
bucket-level permission problem - always check the bucket storage class via
the entry script before concluding a permission gap.

## ossfs 2.0 error attribution (ossfs 2.0 FAQ)

ossfs 2.0 errors carry the HTTP error in the log file; route by message:

| ossfs 2.0 symptom | Attribution | Official guidance (manual only) |
|---|---|---|
| `ERROR: failed to mount ossfs2` + log `Check bucket failed with err: AccessDenied` | permission_403 | AccessKey lacks access to the bucket, or bucket name wrong |
| same + `InvalidAccessKeyId` | creds_invalid | configured AccessKey ID is wrong |
| same + `SignatureDoesNotMatch` | creds_secret | configured AccessKey Secret is wrong |
| `MOUNTPOINT: Directory does not exist` | mountpoint_missing | create the target directory first |
| `MOUNTPOINT: directory ... is not empty` | mountpoint_not_empty | ossfs 2.0 requires an EMPTY directory; umount a previous fs or clean leftovers |
| `version 'FUSE_3.12' not found` | fuse3_missing | ossfs 2.0 needs libfuse3; reinstall the package |
| `fuse: device not found` / `fuse_session_mount failed` | fuse_missing | container without /dev/fuse access; privileged container required |
| write fails `File too large` | size_limit | default 8 MiB part caps files at 78.125 GiB; raise `upload_buffer_size` (more memory, `total_mem_limit` controls the cap) |
| write fails `Invalid argument` | no_random_write | ossfs 2.0 only appends sequentially; random write needs ossfs 1.0, or 2.0.9+ `--temp_dir` |
| `git clone` on the mount fails (ENOENT reads) | write_read_conflict | ossfs 2.0 cannot read a file while it is being written; clone to local disk then copy |
| concurrent write fails `Device or resource busy` | single_writer | only one handle may write a file at a time; single-thread sequential write is the fast path |
| `umount: target is busy` | umount_busy | some process still accesses the mount; `lsof <mountpoint>`, stop it, umount again |
| massive 404 entries in the log | expected_404 | normal existence probing (GetObjectMeta then ListObjects); tune `--attr_timeout` (default 60s) / negative cache (`--oss_negative_cache_size` default 10000, `--oss_negative_cache_timeout` default 0) to cut requests |

## Network / host patterns beyond the basics

- **PrivateLink private mounting (ossfs 1.0, >= 1.91.1)**: set `-ourl` to the
  PrivateLink endpoint domain (`ep-xxxx.oss.<region>.privatelink.aliyuncs.com`)
  and add `-ouse_path_request_style`; official example also passes
  `-osigv4 -oregion=<region>`. A mount configured this way but failing DNS /
  connection should be checked against the VPC endpoint state, not the
  bucket.
- **Auto-mount at boot**: ossfs 2.0 (>= 2.0.6) supports `/etc/fstab` entries
  of type `ossfs2` with `_netdev`; ossfs 1.0 uses the classic fstab pattern.
  "Mount lost after reboot" is a fstab-configuration question, guidance only.
- **Non-root mounting**: `-ouid=<uid> -ogid=<gid>` makes the mounted files
  owned by a non-root user (e.g. `www`); the passwd-ossfs file must be
  readable by the mounting user and a stale mount needs `fusermount -u` by
  that user or root.
- **Application logs on ossfs 1.0**: ossfs 1.0 uploads on close, so
  long-open log files stay local-only until rotation; the official guidance
  pairs ossfs log storage with log rotation. Advise ossfs 2.0 or ossutil for
  such workloads.

## Out of scope for this module

- Endpoint selection questions unrelated to mounting -> skill
  alibabacloud-oss-endpoint-internal-diagnosis.
- Archive restore procedures / lifecycle transitions -> skill
  alibabacloud-oss-lifecycle-runtime-diagnosis.
- Generic cross-account authorization configuration -> skill
  alibabacloud-oss-cross-account-auth-diagnosis.
