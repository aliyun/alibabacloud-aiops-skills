# alibabacloud-sls-php-sdk (OpenAPI)

## Summary

Alibaba Cloud OpenAPI SDK for SLS (PHP). Auto-generated from API metadata — full, consistent API coverage for resource management (Project, Logstore, index, machine group, dashboard, alert, etc.) and log query. This is the newer OpenAPI evolution direction; for basic log writing, use the dedicated PHP SDK.

- Package: `alibabacloud/sls-20201230` (Composer)
- Language / Platform: PHP

## Repository

- GitHub: https://github.com/aliyun/alibabacloud-php-sdk (mono-repo, `sls-20201230` module)

## Official Docs

- OpenAPI overview: https://help.aliyun.com/zh/sls/developer-reference/api-overview
- API list: https://next.api.aliyun.com/document/Sls/2020-12-30/overview
- Per-API doc: `https://next.api.aliyun.com/document/Sls/2020-12-30/<ApiName>` (e.g. `CreateProject`, `GetLogsV2`)
- Online debugging & sample code: `https://next.api.aliyun.com/api/Sls/2020-12-30/<ApiName>?sdkStyle=dara&tab=DEMO&lang=PHP`

## Install

```bash
composer require alibabacloud/sls-20201230 alibabacloud/credentials
```

## Quick Start

```php
use AlibabaCloud\SDK\Sls\V20201230\Sls;
use AlibabaCloud\SDK\Sls\V20201230\Models\GetLogsV2Request;
use AlibabaCloud\Credentials\Credential;
use AlibabaCloud\Credentials\Credential\Config as CredentialConfig;
use Darabonba\OpenApi\Models\Config;

$credentialConfig = new CredentialConfig([
    "type"            => "access_key",
    "accessKeyId"     => getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    "accessKeySecret" => getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
]);
$credential = new Credential($credentialConfig);

$config = new Config([
    "credential" => $credential,
]);
$config->endpoint = "cn-hangzhou.log.aliyuncs.com";
$client = new Sls($config);

$now = time();
$request = new GetLogsV2Request([
    "from" => $now - 3600,
    "to" => $now,
    "query" => "*",
    "line" => 100,
    "offset" => 0,
]);
$response = $client->getLogsV2("your_project", "your_logstore", $request);
echo json_encode($response->body->toMap(), JSON_PRETTY_PRINT);
```

## Capability

| Capability | Ref |
| --- | --- |
| Query logs (`getLogsV2`) | inline |
| Manage resources | inline |

## Notes

- **Do NOT use this SDK for writing logs** — it has no write capability. For `putLogs`, use [aliyun-log-php-sdk](../aliyun-log-php-sdk/index.md).
- Compared to `aliyun-log-php-sdk`, this OpenAPI SDK has broader resource-management API coverage and is the recommended path for new resource-management integrations.
