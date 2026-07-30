# RAM Permission Statement

This Skill does not directly call any OpenAPI that requires RAM authentication.

This Skill needs to read the sqla toolkit from Alibaba Cloud OSS. The minimum permission required is:

| Permission | Description |
|------------|-------------|
| `oss:GetObject` | Used to download the `sqla-3.3.26.tar.gz` toolkit from `cmh-prod-ap-southeast1.oss-ap-southeast-1.aliyuncs.com` |

> This OSS bucket is a public read-only bucket published by the Alibaba Cloud CMH team; in practice `wget` can download it without any additional RAM permission.
