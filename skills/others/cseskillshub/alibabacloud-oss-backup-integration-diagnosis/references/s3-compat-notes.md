# S3 Compatibility Notes

Facts verified from the official Alibaba Cloud OSS documentation
(2026-08):

- S3 compatibility scope and limits:
  https://help.aliyun.com/zh/oss/developer-reference/compatibility-with-amazon-s3
- Access OSS with AWS SDKs (S3-compatible endpoints):
  https://help.aliyun.com/zh/oss/developer-reference/use-aws-sdks-to-access-oss
- V1->V4 signature upgrade guide:
  https://help.aliyun.com/zh/oss/developer-reference/guidelines-for-upgrading-v1-signatures-to-v4-signatures
- Signature version 4 (recommended):
  https://help.aliyun.com/zh/oss/developer-reference/recommend-to-use-signature-version-4

## Endpoint forms (S3-compatible)

| Type | Form |
| --- | --- |
| Public | `https://s3.oss-{region}.aliyuncs.com` |
| Internal (same-region VPC) | `https://s3.oss-{region}-internal.aliyuncs.com` |
| Transfer acceleration | `https://s3.oss-accelerate.aliyuncs.com` |

Replace `{region}` with the region ID, e.g. `cn-hangzhou`. The endpoint
string passed to AWS SDKs must include the scheme (`https://`), otherwise
the SDK raises `The URI scheme of endpointOverride must not be null`
(ticket-verified).

## Request style

OSS supports **only the virtual-hosted request style**: the bucket name
must be a subdomain (`<bucket>.<endpoint>/<key>`). Path-style requests
(`<endpoint>/<bucket>/<key>`) are rejected. S3 clients defaulting to
path-style (e.g. `force_path_style=true`) must be reconfigured.

## Compatible API set (subset relevant to backup tools)

- Bucket: PutBucket, DeleteBucket, GetBucket (ListObjects),
  GetBucketV2 (ListObjectsV2), GetBucketACL, GetBucketLifecycle,
  GetBucketLocation, GetBucketLogging, HeadBucket, PutBucketACL,
  PutBucketLifecycle, PutBucketLogging.
- Object: PutObject, GetObject, HeadObject, DeleteObject, DeleteObjects,
  PostObject, PutObjectCopy, GetObjectACL, PutObjectACL.
- Multipart: InitiateMultipartUpload, UploadPart, UploadPartCopy,
  ListParts, CompleteMultipartUpload, AbortMultipartUpload.
- Through the S3 protocol, `x-oss-process` only supports `image/` and
  `style/` types.

## Known differences that bite backup tools

- **HeadBucket permission mapping**: S3 `HeadBucket` maps to the OSS
  native API `GetBucketInfo`. A RAM policy granting only
  `oss:HeadBucket` yields 403 while ListObjectsV2/GetObject succeed;
  grant `oss:GetBucketInfo` (ticket-verified).
- **ACL model**: OSS only supports S3's private / public-read /
  public-read-write; other S3 ACLs have no equivalent.
- **Storage classes**: Standard / IA / Archive correspond to S3
  STANDARD / STANDARD_IA / GLACIER. S3 restore-days settings are ignored
  by OSS: a restored (unfrozen) archive object stays restored 1 day by
  default, extendable to at most 7 days, then re-freezes.
- **ETag**: OSS PUT ETags are uppercase while S3 tooling may expect
  lowercase; multipart ETag computation differs. Make ETag comparison
  case-insensitive or skip it.
- **Signature**: OSS is phasing out V1 signatures; V4 requires the
  bucket region ID. Tools still signing with V1 are rejected with
  `V1 signature is forbidden`.

## S3-compat enablement and STS error codes (official)

Backup tools hitting these official error codes point at enablement or
header-mapping issues, not at credentials:

| Official error code | Meaning | Guidance |
|---|---|---|
| `0002-00000031` | Amazon S3-compatible request mode is NOT enabled for this account | Switch to OSS-native authentication, or open a support ticket to enable S3 compatibility |
| `0002-00000032` | Amazon S3 V2 signature mode not enabled | Same escalation path |
| `0002-00000033` | Amazon S3 V4 signature mode not enabled | Same escalation path |
| `0002-00000009` | S3-compat requests must not use the `x-oss-security-token` header | STS sessions must send `x-amz-security-token` instead |
| `0017-00000804` | `aws-chunked` encoding conflicts with the `x-amz-content-sha256` value during S3 SDK multipart uploads | Set the header to `STREAMING-AWS4-HMAC-SHA256-PAYLOAD` (official AWS-SDK-access doc) |

Escalation wording for the three "not enabled" codes: the enablement is a
backend action the customer cannot self-serve — submit a support ticket
(account UID + region + tool name); this skill only routes.
