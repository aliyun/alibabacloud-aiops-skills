# Supported Regions (static fallback list)

> Prefer the live list via `safe_aliyun aliyun eflo-controller describe-regions --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou`; this file is only an offline fallback.

## Lingjun supported Region list

| Region ID | Region Name | Endpoint |
|---|---|---|
| `cn-hangzhou` | China East 1 (Hangzhou) | `eflo-controller.cn-hangzhou.aliyuncs.com` |
| `cn-shanghai` | China East 2 (Shanghai) | `eflo-controller.cn-shanghai.aliyuncs.com` |
| `cn-beijing` | China North 2 (Beijing) | `eflo-controller.cn-beijing.aliyuncs.com` |
| `cn-wulanchabu` | China North 6 (Ulanqab) | `eflo-controller.cn-wulanchabu.aliyuncs.com` |
| `cn-shenzhen` | China South 1 (Shenzhen) | `eflo-controller.cn-shenzhen.aliyuncs.com` |
| `ap-southeast-1` | Asia Pacific Southeast 1 (Singapore) | `eflo-controller.ap-southeast-1.aliyuncs.com` |

> [INFO] Available Regions may differ per account and time window; **the live `describe-regions` response is authoritative**. This table is only for emergencies (network unavailable / `describe-regions` failure).

## Default Region for this test suite

The test cases in this repository uniformly use `cn-hangzhou` as the default Region (`TEST_REGION="${TEST_REGION:-cn-hangzhou}"` in `tests/lib/test-helpers.sh`); all fixtures / reports / command examples revolve around that region.
