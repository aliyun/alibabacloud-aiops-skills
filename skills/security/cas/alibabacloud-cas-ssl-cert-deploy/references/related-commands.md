# Related CLI Commands — SSL Certificate Deployment

Complete CLI command reference organized by cloud product.

## CAS (Certificate Authority Service)

| CLI Command | Description |
|-------------|-------------|
| `aliyun cas get-user-certificate-detail` | Query certificate details (domain, SAN list) |
| `aliyun cas list-user-certificate-order` | Search/filter certificates (keyword, status, instance-id, order-type) |
| `aliyun cas list-cloud-resources` | List cloud product resources with domain filtering |
| `aliyun cas create-deployment-job` | Create deployment job (state = editing) |
| `aliyun cas update-deployment-job-status` | Start/modify deployment job state |
| `aliyun cas describe-deployment-job-status` | Query deployment execution statistics |
| `aliyun cas describe-deployment-job` | Query deployment job details |
| `aliyun cas list-worker-resource` | List sub-task workers for failure diagnosis |
| `aliyun cas update-worker-resource-status` | Rollback failed sub-tasks |
| `aliyun cas list-deployment-job` | List all deployment jobs |
| `aliyun cas delete-deployment-job` | Delete deployment job (success/error state only) |
| `aliyun cas update-deployment-job` | Update deployment job config (editing state only) |
| `aliyun cas list-deployment-job-cert` | List certificates in deployment job |
| `aliyun cas list-deployment-job-resource` | List resources in deployment job |
| `aliyun cas list-contact` | List contacts for deployment job |
| `aliyun cas get-instance-detail` | Query certificate instance details |

## CDN

| CLI Command | Description |
|-------------|-------------|
| `aliyun cdn describe-user-domains` | List CDN acceleration domains |
| `aliyun cdn add-cdn-domain` | Create CDN acceleration domain |
| `aliyun cdn describe-cdn-domain-detail` | Poll CDN domain status |
| `aliyun cdn set-cdn-domain-sslcertificate` | **FORBIDDEN** — direct CDN deployment API, must use CAS DeploymentJob instead |
| `aliyun cdn describe-domain-certificate-info` | Verify CDN domain certificate status |

## ALB (Application Load Balancer)

| CLI Command | Description |
|-------------|-------------|
| `aliyun alb list-load-balancers` | List ALB instances |
| `aliyun alb list-listeners` | List listeners for ALB instance |
| `aliyun alb create-listener` | Create HTTPS listener |
| `aliyun alb update-listener-attribute` | Update listener certificate |
| `aliyun alb list-server-groups` | List server groups |
| `aliyun alb create-server-group` | Create server group |
| `aliyun alb add-servers-to-server-group` | Add backend servers to group |
| `aliyun alb list-rules` | List forwarding rules |
| `aliyun alb create-rule` | Create forwarding rule |

## WAF 3.0

| CLI Command | Description |
|-------------|-------------|
| `aliyun waf-openapi describe-instance` | Get WAF instance details |
| `aliyun waf-openapi create-domain` | Onboard domain to WAF 3.0 |

## OSS (via ossutil)

| CLI Command | Description |
|-------------|-------------|
| `ossutil website --method put` | Domain ownership verification / Bind custom domain |

## Supported Cloud Products

| Product | Description | Typical Scenario |
|---------|-------------|------------------|
| CDN | Content Delivery Network | Static asset acceleration |
| SLB | Classic Load Balancer | L4/L7 load balancing |
| ALB | Application Load Balancer | L7 load balancing |
| NLB | Network Load Balancer | L4 load balancing |
| WAF | Web Application Firewall | Security protection |
| OSS | Object Storage Service (custom domain HTTPS) | Static website hosting |
| ESA | Edge Security Acceleration | Edge computing |
