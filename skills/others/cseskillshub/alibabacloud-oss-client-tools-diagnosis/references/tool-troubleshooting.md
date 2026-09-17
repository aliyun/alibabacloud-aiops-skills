# Client Tool Troubleshooting Catalog

Knowledge-driven catalog behind `scripts/_tools_catalog.py`. The sources are
official Alibaba Cloud OSS documentation (verified 2026-08) and root-cause
clusters filtered from the OSS July ticket export. That export contained 81
tickets about ossbrowser, 253 tickets about ossutil errors or connectivity,
35 tickets about login failure, 16 tickets about STS credentials and 4
tickets about clock skew.

## 1. Login failures (ossbrowser)

### 1.1 "AccessDenied: You are forbidden to list buckets"
- Root cause: RAM identity lacks `oss:ListBuckets`; or the account only has
  partial bucket/prefix access by design.
- Fix: grant `oss:ListBuckets`, or keep least privilege by adding the bucket
  path in the preset OSS path field at login and selecting the bucket region.
- Source: ossbrowser FAQ (https://help.aliyun.com/zh/oss/developer-reference/faq-8),
  ossbrowser 2.0 FAQ (https://help.aliyun.com/zh/oss/developer-reference/common-problems).

### 1.2 ossbrowser 2.x login: "The bucket you access does not belong to you" / GetBucketInfo denied
- Root cause (ticket cluster, top login-failure case): ossbrowser 2.x calls
  `GetBucketInfo` at login — a bucket-level action. A directory-scoped policy
  (`acs:oss:*:*:<bucket>/<prefix>/*`) does not cover the bucket-level
  resource, so login fails on 2.x while 1.x (which never calls GetBucketInfo)
  still works. Directory browsing additionally needs `oss:ListObjects`.
- Fix: authorize `oss:GetBucketInfo` + `oss:ListObjects` on
  `acs:oss:*:*:<bucket-name>` without prefix conditions (see the
  least-privilege template in `config-templates.md`).

### 1.3 Old ossbrowser returns 403 although logged in
- Root cause (ticket case): old releases sign with V1 signatures; OSS has
  disabled V1 signing for some APIs, so operations fail with 403 AccessDenied.
- Fix: upgrade to ossbrowser 2.0 (V4 signing).

### 1.4 Login-method questions (AKSK-free login)
- Root cause (ticket case, v1.18.0): ossbrowser 1.x supports AccessKey-pair
  login only; RAM-user password login is a 2.0 feature. Accounts with SSO
  enabled cannot use password login even on 2.0.
- Fix: upgrade to 2.0; under SSO, use an AccessKey pair or authorization code.
- Official ossbrowser 2.0 login methods (login doc): AccessKey pair, account
  QR-scan login through the official mobile apps, STS temporary
  credentials, and authorization code — when a user asks "how do I log in
  without pasting my AK", scan login / authorization code are the official
  answers.

### 1.5 Evidence collection: ossbrowser 2.0 log locations
- For unresolved ossbrowser 2.0 issues, the official FAQ asks for the whole
  `ob2` folder. Default paths:
  - Windows: `C:\Users\<user>\AppData\Roaming\oss-browser2\ob2\`
  - macOS: `/Users/<user>/Library/Application Support/oss-browser2/ob2/`
  - Linux: `~/.config/oss-browser2/ob2/`
- Guide the user to pack and attach it when escalating; this skill never
  reads the logs itself.

## 2. Permission errors (ossutil AccessDenied + EC decision table)

Interpret the EC code from the ossutil error body first:

| EC code | Meaning | Action |
| --- | --- | --- |
| `0003-00000001` | Two official causes: (a) the identity behind the credential lacks permission on this Bucket/Object; (b) the AccessKey ID or the signature is incorrect, so authentication failed. It is NOT limited to a platform-side security policy | Check the AK/SK first (typo, deleted, rotated, wrong account, wrong signature version), then review the RAM/Bucket Policy authorization for the accessed resource |
| `0003-00000101` | Denied by a customer-defined Bucket Policy | Review policy rules (Principal/Action/Resource/Condition) vs the accessed ARN |
| `0003-00000301` | STS session-policy intersection: effective permission = role permissions ∩ AssumeRole session Policy (ticket case: AliyunOSSFullAccess role still denied because the session Policy lacked oss:ListObjectsV2) | Add the missing action to the session Policy as well |

General AccessDenied directions: missing oss action on the accessed resource;
bucket-level actions authorized only on prefix resources; AccessKey IP
whitelist not covering the source IP.

## 3. Credential problems

### 3.1 InvalidAccessKeyId / "The Security Token may be lost"
- Root cause: STS credentials used without the `stsToken` field; or the
  AccessKey ID is deleted/disabled/mis-copied; or the key belongs to a
  different account than the bucket owner.
- Fix: set accessKeyID + accessKeySecret + stsToken together (template in
  `config-templates.md`); re-copy the AK; verify in the RAM console.
- Source: OSS HTTP 403 error-code doc (https://help.aliyun.com/zh/oss/user-guide/http-403-error-code).

### 3.2 RequestTimeTooSkewed (clock skew)
- Root cause: client clock differs from OSS server time by more than
  15 minutes (900 s). Containers/VMs and JVM hosts drift without NTP; the
  displayed time can look correct while the timestamp is off (ticket cases,
  including intermittent ones). Stale pre-signed URLs also trigger it.
- Fix: NTP-sync the client (OSS server time is GMT); ossutil 2.x detects
  RequestTimeTooSkewed and auto-corrects the client time; regenerate
  pre-signed URLs shortly before use.
- Source: HTTP 403 doc above; ossutil 2.0 new features
  (https://help.aliyun.com/zh/oss/developer-reference/ossutil-2-0-new-features).

### 3.3 SecurityTokenExpired
- Root cause: STS token expired mid-transfer or cached without refresh;
  tokens cannot be made permanent by design.
- Fix: refresh via AssumeRole; raise MaxSessionDuration; prefer auto-refresh
  credential modes (RamRoleArn / EcsRamRole).

### 3.4 ossutil cannot connect although the AccessKey is fine
- Root cause (ticket case): an AccessKey network access restriction policy
  (IP whitelist) does not cover the real request source IP.
- Fix: check the key's network restriction policy in RAM; test from another
  network to isolate; check firewall/security group.

## 4. Tool configuration

### 4.1 "region must be set in sign version 4" / "SigningContext.Credentials is null or empty"
- Root cause (ticket case): ossutil 2.x uses V4 signing → region is a
  required config item; credential fields missing in the active profile.
- Fix: `ossutil config set region <region-id>` (must match the bucket
  region) or pass `--region`; verify with `ossutil config get`; check
  `--profile` selection.
- Source: ossutil config doc (https://help.aliyun.com/zh/oss/developer-reference/config-create-configuration-file).

### 4.2 Endpoint / region mismatch
- Root cause: endpoint does not match the bucket region; with STS this
  surfaces as `InvalidSecurityToken` (official example: Qingdao bucket via
  the cn-hangzhou default endpoint). Internal endpoints only work from
  same-region Alibaba Cloud networks.
- Fix: set the matching regional endpoint; deep endpoint-selection strategy
  belongs to alibabacloud-oss-endpoint-internal-diagnosis.

## 5. Connectivity (proxy / firewall / timeouts)

- ossbrowser: broken OS proxy configuration is the documented cause of
  "cannot access due to network reasons" — check Windows Internet options /
  macOS network preferences / Linux system proxy.
- ossutil behind a proxy: `--proxy-host` (HTTP/HTTPS/SOCKS5) plus
  `--proxy-user` / `--proxy-pwd`.
- Timeout tuning (official defaults): `--connect-timeout` 120 s,
  `--read-timeout` 1200 s, `--retry-times` 10 (range 1–500).
- Isolate by testing the same credential from another network.
- Source: ossutil options reference (https://help.aliyun.com/zh/oss/developer-reference/view-options);
  ossbrowser FAQ.

## 6. Version selection (1.0 vs 2.0)

| Aspect | ossbrowser 1.x | ossbrowser 2.x |
| --- | --- | --- |
| Login | AccessKey pair only | + RAM-user password (blocked under SSO) |
| Signing | V1 (some APIs now reject it) | V4 |
| Login permission | no GetBucketInfo | needs bucket-level oss:GetBucketInfo |
| Listing | on-demand | 2.1.1+ caches via background ListObjectsV2 |

| Aspect | ossutil 1.x | ossutil 2.x |
| --- | --- | --- |
| Signing / region | V1 optional region | V4, region REQUIRED |
| Incremental sync | `--update` flag | removed — use `sync --skip-existing` (ticket case) |
| Clock skew | manual | auto-corrects RequestTimeTooSkewed |
| Config | single | profiles, `config set/get`, external/OIDC credentials |

- Source: ossutil 2.0 new features doc above; migration guide referenced
  therein.

## 7. Official tool map and selection (oss-tools overview)

When the question is "which tool should I use" rather than "why does my
tool fail", route with the official catalog
(https://help.aliyun.com/zh/oss/developer-reference/oss-tools):

| Need | Official recommendation |
|---|---|
| Command line / automation | ossutil 2.0 (recommended; advanced + API-level commands, external/OIDC credentials, `--output-format` JSON/YAML/XML); Alibaba Cloud CLI for cross-product management |
| GUI browsing | ossbrowser 2.0 (recommended; scan login, favorites, in-place editing of small text files) |
| Mount as filesystem | ossfs 2.0 / 1.0 → skill alibabacloud-oss-ossfs-mount-diagnosis |
| Migration into OSS | Online Migration Service (S3/COS/OBS/TOS/GCS/Azure etc.), ossimport (Java 7, distributed), Lightning Cube offline for TB-PB |
| FTP clients (FileZilla/WinSCP) | ossftp server (Python 2.7 based) |
| AI/ML training data | OSS Connector for AI/ML (Linux x86-64, Python 3.8-3.12, PyTorch >= 2.0) |
| Manual signature debugging | console signature tools (Header / PostObject Policy / URL signing) — NOTE: they generate V1 signatures ONLY, so they cannot reproduce V4 problems |
| Policy authoring | RAM policy editor (console) |

Retirement facts worth stating verbatim: **osscmd was retired on
2019-07-31** (Python 2.5-2.7 only; replaced by ossutil) — a user still on
osscmd should migrate to ossutil, not debug osscmd.

## 8. Tool limits that generate tickets (official)

- ossbrowser moves/copies only files <= 5 GB; single-file upload cap is
  48.8 TB (multipart); downloads through ossbrowser generate downstream
  traffic fees like any public download.
  - Source (48.8 TB / 5 GB, 4-way cross-verified 2026-09-03):
    https://help.aliyun.com/zh/oss/how-to-upload-large-objects-to-oss ,
    https://help.aliyun.com/zh/oss/developer-reference/commonly-used-function-of-ossbrowser2-0 ,
    https://help.aliyun.com/zh/oss/developer-reference/use-ossbrowser ,
    https://help.aliyun.com/zh/oss/user-guide/limits
- ossbrowser in CloudBox environments cannot generate share-link downloads
  or preview images (official FAQ) — not a permission bug.
- ossbrowser 2.0 "fetched N items"-style cached listings come from background
  ListObjectsV2 since 2.1.1; refresh / prefix search / directory switch
  clears the cache — "missing file" reports right after a remote change
  may simply be the local cache.
