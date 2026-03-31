# DataWorks Service Endpoints

> Official Documentation: https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-endpoint

## Asia Pacific

| Region Name | RegionId | Public Endpoint |
|-------------|----------|-----------------|
| China East 1 (Hangzhou) | cn-hangzhou | dataworks.cn-hangzhou.aliyuncs.com |
| China East 2 (Shanghai) | cn-shanghai | dataworks.cn-shanghai.aliyuncs.com |
| China South 1 (Shenzhen) | cn-shenzhen | dataworks.cn-shenzhen.aliyuncs.com |
| China North 2 (Beijing) | cn-beijing | dataworks.cn-beijing.aliyuncs.com |
| China North 3 (Zhangjiakou) | cn-zhangjiakou | dataworks.cn-zhangjiakou.aliyuncs.com |
| China North 6 (Ulanqab) | cn-wulanchabu | dataworks.cn-wulanchabu.aliyuncs.com |
| China Southwest 1 (Chengdu) | cn-chengdu | dataworks.cn-chengdu.aliyuncs.com |
| China Hong Kong | cn-hongkong | dataworks.cn-hongkong.aliyuncs.com |
| Singapore | ap-southeast-1 | dataworks.ap-southeast-1.aliyuncs.com |
| Malaysia (Kuala Lumpur) | ap-southeast-3 | dataworks.ap-southeast-3.aliyuncs.com |
| Indonesia (Jakarta) | ap-southeast-5 | dataworks.ap-southeast-5.aliyuncs.com |
| South Korea (Seoul) | ap-northeast-2 | dataworks.ap-northeast-2.aliyuncs.com |
| Japan (Tokyo) | ap-northeast-1 | dataworks.ap-northeast-1.aliyuncs.com |

## Europe and Americas

| Region Name | RegionId | Public Endpoint |
|-------------|----------|-----------------|
| Germany (Frankfurt) | eu-central-1 | dataworks.eu-central-1.aliyuncs.com |
| UK (London) | eu-west-1 | dataworks.eu-west-1.aliyuncs.com |
| US (Virginia) | us-east-1 | dataworks.us-east-1.aliyuncs.com |
| US (Silicon Valley) | us-west-1 | dataworks.us-west-1.aliyuncs.com |

## Middle East

| Region Name | RegionId | Public Endpoint |
|-------------|----------|-----------------|
| UAE (Dubai) | me-east-1 | dataworks.me-east-1.aliyuncs.com |
| Saudi Arabia (Riyadh) | me-central-1 | dataworks.me-central-1.aliyuncs.com |

## Industry Cloud

| Region Name | RegionId | Public Endpoint |
|-------------|----------|-----------------|
| China South 1 Finance Cloud | cn-shenzhen-finance-1 | dataworks.cn-shenzhen-finance-1.aliyuncs.com |
| China East 2 Finance Cloud | cn-shanghai-finance-1 | dataworks.cn-shanghai-finance-1.aliyuncs.com |
| China East 1 Finance Cloud | cn-hangzhou-finance | dataworks.aliyuncs.com |

---

## Usage Instructions

When executing CLI commands, you must add the corresponding `--region` and `--endpoint` parameters based on the user-specified region:

```bash
--region {RegionId} --endpoint dataworks.{RegionId}.aliyuncs.com
```

**Examples**:
- South Korea: `--region ap-northeast-2 --endpoint dataworks.ap-northeast-2.aliyuncs.com`
- Shanghai: `--region cn-shanghai --endpoint dataworks.cn-shanghai.aliyuncs.com`
