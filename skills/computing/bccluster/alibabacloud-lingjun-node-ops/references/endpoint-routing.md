> Index summary; this document is the **single source of truth** for all four hard rules referenced from `SKILL.md`.

## Rule 1 - Endpoint must match Region (eflo-controller only)

Every `aliyun eflo-controller <action>` invocation **must** include both:

```bash
--region <region>
--endpoint eflo-controller.<region>.aliyuncs.com
```

`<region>` in `--region` and in the endpoint host **must be identical**, otherwise the server returns `InvalidRegionId`.

**Counter-examples (forbidden)**:

```bash
# [FAIL] Region mismatch
aliyun eflo-controller list-clusters --region cn-hangzhou \
  --endpoint eflo-controller.cn-wulanchabu.aliyuncs.com

# [FAIL] Missing endpoint (CLI may pick the default cn-hangzhou which mismatches the region)
aliyun eflo-controller list-clusters --region cn-wulanchabu
```

**bssopenapi / ResourceManager are exempt** from the region-matching rule - they use the billing gateway. For `bssopenapi` (billing gateway) try in this order:

```bash
# 1st: China-site central gateway
aliyun bssopenapi renew-instance --endpoint business.aliyuncs.com --instance-id e01-... --product-code bccluster ...
# 2nd (only if the above is unreachable or site-mismatched, e.g. "Product code is invalid"):
aliyun bssopenapi renew-instance --endpoint business.ap-southeast-1.aliyuncs.com --instance-id e01-... --product-code bccluster ...
```

Keep the same `--client-token` value across the fallback retry.

## Rule 2 - Region is required (no silent default)

When the user has not explicitly named a Region:

- [FAIL] The Agent **must not** default to `cn-hangzhou` / `cn-wulanchabu` / any prior-turn value.
- [FAIL] The Agent **must not** pick a Region by inspecting the AccessKey owner's billing region.
- [OK] The Agent **must** HITL the user with the list returned by `describe-regions`.

**Sole exception**: `describe-regions` itself may use `cn-hangzhou` once as a discovery seed:

```bash
safe_aliyun aliyun eflo-controller describe-regions \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou
```

## Rule 3 - Multi-Region enumeration intent

When the user says "all my nodes / list everything / what nodes do I have" (or the equivalent in any language), the Agent **must not** answer after a single-region query. Required HITL two-way pick:

- A. Iterate every region returned by `describe-regions`, aggregate by region.
- B. Specify a single region (user picks one).

Under choice A, a single-region failure does **not** abort the iteration; the final answer must explicitly note `iterated N / succeeded M / failed K`. **Never** equate "successfully iterated 0 records" with "iteration did not succeed".

## Rule 4 - Test region `cn-wulanchabu-test-6` mandatory `--insecure`

When the user-specified Region is `cn-wulanchabu-test-6`, **all** CLIs (read & write, including `aliyun bssopenapi *`) **must** uniformly append `--insecure`:

```bash
safe_aliyun aliyun eflo-controller list-clusters \
  --region cn-wulanchabu-test-6 \
  --endpoint eflo-controller.cn-wulanchabu-test-6.aliyuncs.com \
  --insecure
```

Reason: the test gateway uses a self-signed certificate. The bundled `safe_aliyun` wrapper auto-injects `--insecure` whenever it sees the test region in the argument list. Do **not** omit it from any single command. Do **not** apply `--insecure` to other production regions.

## Endpoint inventory (production)

| Region | Endpoint |
|---|---|
| `cn-hangzhou` | `eflo-controller.cn-hangzhou.aliyuncs.com` |
| `cn-shanghai` | `eflo-controller.cn-shanghai.aliyuncs.com` |
| `cn-beijing` | `eflo-controller.cn-beijing.aliyuncs.com` |
| `cn-wulanchabu` | `eflo-controller.cn-wulanchabu.aliyuncs.com` |
| `cn-shenzhen` | `eflo-controller.cn-shenzhen.aliyuncs.com` |
| `cn-heyuan` | `eflo-controller.cn-heyuan.aliyuncs.com` |
| `cn-zhangjiakou` | `eflo-controller.cn-zhangjiakou.aliyuncs.com` |
| `ap-southeast-1` (Singapore) | `eflo-controller.ap-southeast-1.aliyuncs.com` |
| `cn-wulanchabu-test-6` (test) | `eflo-controller.cn-wulanchabu-test-6.aliyuncs.com` (+ `--insecure`) |

The authoritative list comes from `describe-regions`; this table is a fast-path reference only.
