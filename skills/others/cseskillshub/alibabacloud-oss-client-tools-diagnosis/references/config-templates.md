# Configuration Templates

Templates are embedded as constants in `scripts/_tools_catalog.py` and are
emitted by the entry script when the matched diagnosis needs them. They are
OUTPUT for the user to fill and apply locally — the Agent never applies them.

## 1. ossutil credential configuration template

Field names follow the official ossutil `config` command documentation
(https://help.aliyun.com/zh/oss/developer-reference/config-create-configuration-file).
Placeholder values only; the skill never accepts real credentials.

```ini
[default]
# Credential fields — fill both locally, never paste the values into chat:
#   accessKeyID     -> your AccessKey ID
#   accessKeySecret -> your AccessKey Secret
# stsToken is REQUIRED when using STS temporary credentials; omit for AK
stsToken=<SecurityToken from AssumeRole>
# region is REQUIRED by ossutil 2.x (V4 signature); must match the bucket region
region=cn-hangzhou
# endpoint is optional; defaults to the region's public endpoint
# endpoint=https://oss-cn-hangzhou.aliyuncs.com
```

Usage notes:
- The error message "The Security Token may be lost" means that the
  `stsToken` field is missing while the key pair is an STS temporary
  credential.
- The error message "region must be set in sign version 4" means that the
  `region` field is missing. Set it with
  `ossutil config set region <region-id>` or pass `--region`.
- Behind a proxy add `--proxy-host` (+ `--proxy-user`/`--proxy-pwd`);
  timeouts: `--connect-timeout` (default 120 s), `--read-timeout`
  (default 1200 s), `--retry-times` (default 10, range 1–500) — official
  ossutil options reference.

## 2. Least-privilege RAM policy template

Distilled from ticket resolutions for ossbrowser/ossutil users with
directory-scoped access. Key points:
- ossbrowser 2.x login needs bucket-level `oss:GetBucketInfo` (prefix
  conditions are not supported for this action).
- Directory browsing needs bucket-level `oss:ListObjects`.
- `oss:ListBuckets` can be dropped if the user logs in via the preset OSS
  path field instead of the bucket list.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["oss:ListBuckets"],
      "Resource": ["acs:oss:*:*:*"]
    },
    {
      "Effect": "Allow",
      "Action": ["oss:GetBucketInfo", "oss:ListObjects"],
      "Resource": ["acs:oss:*:*:<bucket-name>"]
    },
    {
      "Effect": "Allow",
      "Action": ["oss:GetObject", "oss:PutObject", "oss:DeleteObject"],
      "Resource": ["acs:oss:*:*:<bucket-name>/<prefix>/*"]
    }
  ]
}
```

Replace `<bucket-name>` and `<prefix>` with the real values; drop actions the
user does not need (read-only access keeps `oss:GetObject` only).

## 3. STS session-policy reminder

When the client authenticates with STS, the effective permission is the
intersection of the role's permissions and the AssumeRole session Policy.
Any action missing from the session Policy is denied even if the role holds
AliyunOSSFullAccess (EC `0003-00000301`). Mirror the actions above into the
session Policy as well.
