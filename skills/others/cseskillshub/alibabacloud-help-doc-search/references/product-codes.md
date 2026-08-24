# Help Center Product Codes

Product codes used in help-center URLs (`https://help.aliyun.com/zh/{product_code}/`)
and in the `-p/--product` option of `scripts/aliyun_help.py`. Codes are lowercase.

## Quick reference

| Code | Product |
|---|---|
| `ecs` | Elastic Compute Service |
| `oss` | Object Storage Service |
| `rds` | ApsaraDB RDS |
| `slb` | Server Load Balancer |
| `vpc` | Virtual Private Cloud |
| `eip` | Elastic IP Address (a separate product from VPC; see aliases below) |
| `cdn` | Content Delivery Network |
| `ack` | Container Service for Kubernetes |
| `functioncompute` | Function Compute (**not** `fc`; `fc` only 301-redirects) |
| `nas` | File Storage NAS |
| `dns` | Alibaba Cloud DNS |
| `ram` | Resource Access Management |
| `sts` | Security Token Service |
| `kms` | Key Management Service |
| `waf` | Web Application Firewall |
| `ddos` | Anti-DDoS |
| `cms` | CloudMonitor |
| `sls` | Simple Log Service |
| `api-gateway` | API Gateway |
| `mns` | Message Service |
| `rocketmq` | Message Queue for RocketMQ |
| `kafka` | Message Queue for Apache Kafka |
| `elasticsearch` | Elasticsearch |
| `dataworks` | DataWorks |
| `maxcompute` | MaxCompute |
| `pai` | Platform for AI |
| `model-studio` | Model Studio |
| `actiontrail` | ActionTrail |

## Aliases and non-obvious codes

Common aliases and product relationships that frequently cause empty results:

| What you might type | Correct code | Note |
|---|---|---|
| `fc` | `functioncompute` | Function Compute's canonical code is `functioncompute`; `fc` only 301-redirects and breaks llms.txt fetches |
| EIP / Elastic IP (under `vpc`?) | `eip` | Elastic IP Address is an independent product with its own code `eip`, **not** part of `vpc` |

Rules of thumb:

- When a product-scoped search returns nothing, suspect the code first: verify it
  with `list-products`, then retry with the canonical code (or without `-p`).
- Codes can be verified against the help-center catalog at any time:
  `python3 scripts/aliyun_help.py list-products` prints every valid code.

## Caveats

- Most codes match the product's English name, but there are exceptions (Function
  Compute is `functioncompute`, not `fc`).
- Some products use numeric IDs as codes (for example, vector search uses `2510217`).
  Use `list-products` to discover them.
- Help-center codes (lowercase, e.g. `actiontrail`) belong to a different system than
  OpenAPI metadata codes (PascalCase, e.g. `Actiontrail`). The script's `api-*`
  subcommands normalize case automatically; raw `curl` calls against the meta endpoints
  require exact casing (the `api-products` output shows the exact casing for every
  product).
- The llms.txt indexes cover China-site Chinese documentation; international-site
  documentation lives under `alibabacloud.com/help/`.
