# APIG Platform Plugin OCI Registry

Built-in platform plugin images are hosted in a **region-specific VPC registry**. This file is the authoritative source for constructing `PLATFORM_OCI_BASE` when built-in plugins are needed in Step 3a.

## OCI URL Format

```
oci://apiginner-registry-vpc.<REGION>.cr.aliyuncs.com/platform_wasm/<plugin-name>:<version>
```

Set `PLATFORM_OCI_BASE` to the base path for the cluster's region, then append plugin name and version:

```
PLATFORM_OCI_BASE=apiginner-registry-vpc.<REGION>.cr.aliyuncs.com/platform_wasm

# Full URL example:
oci://${PLATFORM_OCI_BASE}/waf:1.0.0
```

## Determine Cluster Region

**Auto-detect via kubectl** (preferred):

```bash
kubectl get nodes -o jsonpath='{.items[0].metadata.labels.topology\.kubernetes\.io/region}' 2>/dev/null || \
kubectl get nodes -o jsonpath='{.items[0].spec.providerID}' | grep -oP '(?<=\.)[a-z]+-[a-z]+-?\d*(?=\.)'
```

If auto-detection fails, **ask the user** which region their APIG instance is in.

## Region → PLATFORM_OCI_BASE Table

| Area | Region | Region ID | PLATFORM_OCI_BASE |
|------|--------|-----------|-------------------|
| China | Qingdao | `cn-qingdao` | `apiginner-registry-vpc.cn-qingdao.cr.aliyuncs.com/platform_wasm` |
| | Beijing | `cn-beijing` | `apiginner-registry-vpc.cn-beijing.cr.aliyuncs.com/platform_wasm` |
| | Zhangjiakou | `cn-zhangjiakou` | `apiginner-registry-vpc.cn-zhangjiakou.cr.aliyuncs.com/platform_wasm` |
| | Ulanqab | `cn-wulanchabu` | `apiginner-registry-vpc.cn-wulanchabu.cr.aliyuncs.com/platform_wasm` |
| | Hangzhou | `cn-hangzhou` | `apiginner-registry-vpc.cn-hangzhou.cr.aliyuncs.com/platform_wasm` |
| | Shanghai | `cn-shanghai` | `apiginner-registry-vpc.cn-shanghai.cr.aliyuncs.com/platform_wasm` |
| | Shenzhen | `cn-shenzhen` | `apiginner-registry-vpc.cn-shenzhen.cr.aliyuncs.com/platform_wasm` |
| | Chengdu | `cn-chengdu` | `apiginner-registry-vpc.cn-chengdu.cr.aliyuncs.com/platform_wasm` |
| | Hong Kong | `cn-hongkong` | `apiginner-registry-vpc.cn-hongkong.cr.aliyuncs.com/platform_wasm` |
| Asia Pacific | Tokyo | `ap-northeast-1` | `apiginner-registry-vpc.ap-northeast-1.cr.aliyuncs.com/platform_wasm` |
| | Singapore | `ap-southeast-1` | `apiginner-registry-vpc.ap-southeast-1.cr.aliyuncs.com/platform_wasm` |
| | Jakarta | `ap-southeast-5` | `apiginner-registry-vpc.ap-southeast-5.cr.aliyuncs.com/platform_wasm` |
| | Seoul | `ap-northeast-2` | `apiginner-registry-vpc.ap-northeast-2.cr.aliyuncs.com/platform_wasm` |
| | Kuala Lumpur | `ap-southeast-3` | `apiginner-registry-vpc.ap-southeast-3.cr.aliyuncs.com/platform_wasm` |
| Europe & Americas | Silicon Valley | `us-west-1` | `apiginner-registry-vpc.us-west-1.cr.aliyuncs.com/platform_wasm` |
| | Virginia | `us-east-1` | `apiginner-registry-vpc.us-east-1.cr.aliyuncs.com/platform_wasm` |
| | Frankfurt | `eu-central-1` | `apiginner-registry-vpc.eu-central-1.cr.aliyuncs.com/platform_wasm` |
| Finance Cloud | Shanghai Finance | `cn-shanghai-finance-1` | `apiginner-registry-vpc.cn-shanghai-finance-1.cr.aliyuncs.com/platform_wasm` |

Full region list: https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/product-overview/regions
