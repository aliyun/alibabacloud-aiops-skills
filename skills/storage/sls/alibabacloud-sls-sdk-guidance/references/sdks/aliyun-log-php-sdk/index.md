# aliyun-log-php-sdk

## Summary

PHP SDK for Alibaba Cloud SLS. Wraps the SLS API behind `Aliyun_Log_Client`: write (`putLogs`), query (`getLogs`, histograms, batch), Shard management, and log shipping (Shipper). Includes a simple logger with local batch cache.

- Package: `alibabacloud/aliyun-log-php-sdk` (Composer)
- Language / Platform: PHP 5.2.1+

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-php-sdk

## Official Docs

- Overview: https://help.aliyun.com/zh/sls/developer-reference/php-sdk/
- Install: https://help.aliyun.com/zh/sls/developer-reference/install-log-service-sdk-for-php
- Quick Start: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-php

## Install

```bash
composer require alibabacloud/aliyun-log-php-sdk
```

## Quick Start

```php
require_once realpath(dirname(__FILE__).'/vendor/autoload.php');

$client = new Aliyun_Log_Client(
    'cn-hangzhou.log.aliyuncs.com',
    getenv('ALIBABA_CLOUD_ACCESS_KEY_ID'),
    getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET'), '');
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Basic / batch (`putLogs`) | inline |
| Query logs (`getLogs`) | inline |
| Manage resources | inline |
