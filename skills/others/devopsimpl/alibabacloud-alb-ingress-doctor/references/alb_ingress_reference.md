# ALB Ingress Concepts and Annotation Reference

## Architecture Concepts

### AlbConfig
- CRD resource, one-to-one mapping to ALB instance
- Defines: listener port/protocol, certificate, availability zone (zoneMappings), access control, logging, tags, etc.
- listeners uses **replace-style update**, patch must pass the complete listeners array

### IngressClass
- Bridges Ingress and AlbConfig
- `spec.controller: ingress.k8s.alibabacloud.com/alb` (note: must include `.com`)
- `spec.parameters.name` points to the AlbConfig name
- **Binding chain**: `Ingress.spec.ingressClassName` → `IngressClass.metadata.name` → `IngressClass.spec.parameters.name` → `AlbConfig.metadata.name`. Any broken link causes routes to not take effect.
- Complete YAML example:
```yaml
apiVersion: networking.k8s.io/v1
kind: IngressClass
metadata:
  name: alb
spec:
  controller: ingress.k8s.alibabacloud.com/alb
  parameters:
    apiGroup: alibabacloud.com
    kind: AlbConfig
    name: <albconfig-name>
```

### Ingress
- Defines routing rules, TLS configuration, backend Service
- `spec.ingressClassName` points to IngressClass
- Configures listener port, backend protocol, canary and other advanced features via annotations

### ALB Ingress Controller
- Managed component, watches K8s resource changes and syncs to ALB
- v2.11.0+ does not auto-create listeners, must explicitly define them in AlbConfig
- Each reconcile performs a full update of all forwarding rules under that listener

---

## Core Annotation Dictionary

### Listener and Protocol

| Annotation | Description | Example Value |
|------------|-------------|---------------|
| listen-ports | Listener port (JSON array) | `'[{"HTTP":80},{"HTTPS":443}]'` |
| backend-protocol | Backend protocol | `https` / `grpc` |
| ssl-redirect | HTTP->HTTPS redirect (automatically references port 80) | `"true"` |

### Path Matching and Rewrite

| Annotation | Description | Example Value |
|------------|-------------|---------------|
| use-regex | Enable regex matching | `"true"` |
| rewrite-target | URL rewrite target | `/$2` |

**IMPORTANT — Regex path rules:**
- When using regex paths (containing `(.*)`, `+`, `?`, etc.), `pathType` **MUST** be set to `Prefix` (NOT `ImplementationSpecific` or `Exact`)
- Must add annotation `alb.ingress.kubernetes.io/use-regex: "true"`
- Failure to set `pathType: Prefix` with regex characters causes `RULE_PATH_ILLEGAL` error

Correct regex path example:
```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/use-regex: "true"
spec:
  rules:
  - http:
      paths:
      - path: /api/(.*)
        pathType: Prefix
        backend:
          service:
            name: my-svc
            port:
              number: 80
```

Note: When using rewrite-target, pathType must also be Prefix

### Canary Release

| Annotation | Description | Example Value |
|------------|-------------|---------------|
| canary | Enable canary | `"true"` |
| canary-by-header | Canary based on Header | `"gray"` |
| canary-by-header-value | Header match value | `"always"` |
| canary-by-cookie | Canary based on Cookie | `"gray"` |
| canary-weight | Weight-based canary (0-100) | `"30"` |

Priority: Header > Cookie > Weight

### Session Affinity

| Annotation | Description | Example Value |
|------------|-------------|---------------|
| sticky-session | Enable session affinity | `"true"` |
| sticky-session-type | Type | `Insert` / `Server` |
| cookie | Cookie name (required for Server mode) | `"SERVERID"` |
| cookie-timeout | Expiration time (Insert mode) | `"1800"` |

### Rate Limiting and Load Balancing

| Annotation | Description | Example Value |
|------------|-------------|---------------|
| traffic-limit-qps | QPS rate limit [1,1000000] | `"100"` |
| backend-scheduler | Scheduling algorithm | `wrr`/`wlc`/`sch`/`uch` |
| slow-start-enabled | Slow start | `"true"` |
| slow-start-duration | Slow start duration (30-900 seconds) | `"60"` |

Note: Slow start only supports wrr algorithm

### Health Check

| Annotation | Description | Example Value |
|------------|-------------|---------------|
| healthcheck-enabled | Enable health check | `"true"` |
| healthcheck-protocol | Protocol | `HTTP`/`HTTPS`/`TCP`/`GRPC` |
| healthcheck-path | Check path | `"/health"` |
| healthcheck-method | Method | `HEAD`/`GET`/`POST` |

### Cross-Origin (CORS)

| Annotation | Description | Example Value |
|------------|-------------|---------------|
| enable-cors | Enable CORS | `"true"` |
| cors-allow-origin | Allowed origin | `"*"` |
| cors-allow-methods | Allowed methods | `"GET,POST,PUT"` |
| cors-allow-headers | Allowed headers | `"Content-Type"` |

---

## Flannel vs Terway Impact on Service Type

- **Flannel cluster**: ALB Ingress only supports NodePort / LoadBalancer type Service
- **Terway cluster**: Supports ClusterIP (ENI direct connection mode)
- **Older Terway (v1.22 and below)**: May use ECS mount mode, needs manual addition of `service.beta.kubernetes.io/backend-type: "eni"` annotation

---

## ALB Instance Edition Requirements

- **Basic Edition**: Does not support Ingress Controller management
- **Standard Edition**: Default edition, supports Controller
- **WAF Enhanced Edition (StandardWithWaf)**: Must explicitly set `edition: StandardWithWaf` in AlbConfig

---

## Three Certificate Configuration Methods

1. **Auto-discovery**: Ingress spec.tls.hosts configures domain (do not fill in secretName), ALB auto-matches from SSL console. If the tls field is not configured, but the Ingress annotation `listen-ports: '[{"HTTPS": 443}]'` is configured to specify an HTTPS listener port, certificate auto-discovery will also be enabled. Auto-discovery pulls all certificates matching the domain, without distinguishing validity period or algorithm.
2. **K8s Secret**: Ingress spec.tls.secretName references a TLS Secret (cross-namespace not supported). Controller uploads the certificate from the Secret to the SSL certificate console, with naming format `namespace-secretname-random-string`, then associates it with the ALB listener.
3. **AlbConfig specified**: Directly bind CertificateId (format: `number-region`) in listeners.certificates. v2.19.1+ supports defaultCertificate field, which has higher priority than certificates.IsDefault.

### Certificate Usage Configuration Examples

**AlbConfig specifying certificate ID:**
```yaml
listeners:
  - port: 443
    protocol: HTTPS
    certificates:
    - CertificateId: 13905564-cn-hangzhou
      IsDefault: true
    - CertificateId: 14261892-cn-hangzhou
```

**defaultCertificate (v2.19.1+):**
```yaml
listeners:
  - port: 443
    protocol: HTTPS
    defaultCertificate:
      kind: CertIdentifier
      certificateId: 75****-hangzhou
    certificates:
      - CertificateId: 75****-hangzhou
        IsDefault: true
```

**Certificate auto-discovery (Ingress side):**
```yaml
spec:
  ingressClassName: alb
  rules:
  - host: www.example.com
    http:
      paths:
      - path: /
        pathType: ImplementationSpecific
        backend:
          service:
            name: my-svc
            port:
              number: 80
  tls:
  - hosts:
    - www.example.com
```

**Secret certificate (Ingress side):**
```yaml
spec:
  ingressClassName: alb
  tls:
  - hosts:
    - demo.alb.ingress.top
    secretName: https-secret
```

---

## ALB Certificate Matching Priority

When multiple certificates exist for the same HTTPS listener and same domain, ALB selects the certificate by the following priority:

1. **ECC algorithm certificate has the highest matching priority**
2. Among RSA algorithm certificates, **extension certificate priority is higher than default certificate**
3. Among RSA extension certificates, **certificate with longer validity period has higher matching priority**

## Certificate Association Compatibility

| Combination Scenario | Behavior |
|---------------------|----------|
| Auto-discovery + Secret (same domain) | Secret certificate has higher priority |
| Auto-discovery + Secret (different domains) | Each domain independently selects the corresponding certificate |
| Auto-discovery + AlbConfig specified certificate (same Listener) | **AlbConfig specified certificate takes priority, auto-discovery does not take effect** |
| Secret + AlbConfig specified certificate (same Listener) | Coexists compatibly; when certificate content is the same, the one with longer validity period takes effect |

### Certificate Diagnosis Key Points

- **AlbConfig specified certificate and auto-discovery are incompatible**: After configuring AlbConfig listeners.certificates, Ingress auto-discovery for the same Listener will not pull certificates
- **defaultCertificate has the highest priority** (v2.19.1+): defaultCertificate priority is higher than certificates.IsDefault; after configuring defaultCertificate, certificates.IsDefault automatically becomes ineffective
- **defaultCertificate can be combined with auto-discovery**: defaultCertificate manages the default certificate, auto-discovered certificates enter the extension certificate list
- **Auto-discovery pulls without differentiation**: Auto-discovery pulls all certificates matching the domain, without distinguishing validity period or algorithm type

## Certificate Auto-Discovery Update Common Issues

### Scenario: After updating a certificate, access still shows the old certificate

**Typical flow:**
1. The certificate deployed by auto-discovery is the default certificate of the HTTPS listener
2. The user replaces the default certificate with a new certificate via the ALB console or the digital certificate one-click deployment feature
3. After K8s triggers a reconcile, auto-discovery re-associates the old certificate to the ALB listener's **extension certificate list**
4. ALB certificate matching logic: extension certificate > default certificate -> the old extension certificate is matched first

**Fix:**
- **v2.18+ (recommended)**: Configure defaultCertificate in AlbConfig to specify the old certificate (or another non-associated domain certificate) as the default certificate. After triggering a reconcile, the new certificate enters the extension certificate list and is matched first
- **Lower versions**: Replace the default certificate with another non-associated access domain certificate in the ALB console, re-trigger a reconcile, and the new certificate enters the extension certificate list

---

## Quota Limits Reference

> How to increase quotas: Go to Alibaba Cloud Quota Center > Load Balancing > Application Load Balancer ALB tab to apply for an increase. Quotas that cannot be adjusted require a support ticket.
> Note: If a resource is associated multiple times within the statistical scope, the quota calculation is cumulative. For example, when the same backend server is associated with multiple listeners and forwarding rules, it is counted multiple times.

### Usage Limits (Hard limits that cannot be increased)

#### Listener Limits

| Resource | Basic Edition | Standard/WAF Enhanced Edition |
|----------|---------------|-------------------------------|
| Number of access control policy groups that can be associated with a listener | 3 | 3 |
| Number of access control entries that can be associated with a listener | 300 | 500 |

#### Forwarding Rule Limits

| Resource | Basic Edition | Standard/WAF Enhanced Edition |
|----------|---------------|-------------------------------|
| Number of action entries that can be added to a forwarding rule | 3 | 5 |
| Number of match condition entries that can be added to a forwarding rule | 5 | 10 |
| Number of entries with wildcards that can be added to a forwarding rule | 5 | 10 |

#### Server Group Limits

| Resource | All Editions |
|----------|--------------|
| Number of backend servers (IP and port) that can be added to a server group | 1000 |

#### Access Control and Security Policy Limits

| Resource | All Editions |
|----------|--------------|
| Number of listeners that can be associated with an access control policy group | 50 |
| Number of entries that can be added to an access control policy group | 500 |
| Number of listeners that can be associated with a custom security policy | 10 |
| Number of access control entries that can be associated with an ALB instance | 800 |

#### Regional Limits

| Resource | All Editions |
|----------|--------------|
| Number of custom security policies supported per region | 50 |
| Number of health check templates supported per region | 50 |
| Number of access control policy groups supported per region | 1000 |
| Number of server groups supported per region | 3000 |

### General Quotas (Can apply for increase)

#### Instance Quotas

| Quota ID | Description | Default | Maximum Increase To |
|----------|-------------|---------|---------------------|
| alb_quota_loadbalancers_num | Number of ALB instances supported per region | 60 | 150 |

#### Basic Edition ALB Instance Quotas

| Quota ID | Description | Default | Maximum Increase To |
|----------|-------------|---------|---------------------|
| alb_quota_loadbalancer_certificates_num_basic_edition | Extension certificate count (not counting default certificate) | 10 | 150 |
| alb_quota_loadbalancer_rules_num_basic_edition | Forwarding rule count (not counting default rule) | 40 | 100 |
| alb_quota_loadbalancer_servers_num_basic_edition | Backend server count | 200 | 400 |
| alb_quota_loadbalancer_listeners_num_basic_edition | Listener count | 50 | 80 |

#### Standard Edition ALB Instance Quotas

| Quota ID | Description | Default | Maximum Increase To |
|----------|-------------|---------|---------------------|
| alb_quota_loadbalancer_certificates_num_standard_edition | Extension certificate count (not counting default certificate) | 25 | 300 |
| alb_quota_loadbalancer_rules_num_standard_edition | Forwarding rule count (not counting default rule) | 100 | 200 |
| alb_quota_loadbalancer_servers_num_standard_edition | Backend server count | 1000 | 1500 |
| alb_quota_loadbalancer_listeners_num_standard_edition | Listener count | 50 | 100 |

#### WAF Enhanced Edition ALB Instance Quotas

| Quota ID | Description | Default | Maximum Increase To |
|----------|-------------|---------|---------------------|
| alb_quota_loadbalancer_certificates_num_standardwithwaf_edition | Extension certificate count (not counting default certificate) | 25 | 300 |
| alb_quota_loadbalancer_rules_num_standardwithwaf_edition | Forwarding rule count (not counting default rule) | 100 | 200 |
| alb_quota_loadbalancer_servers_num_standardwithwaf_edition | Backend server count | 1000 | 1500 |
| alb_quota_loadbalancer_listeners_num_standardwithwaf_edition | Listener count | 50 | 100 |

#### Listener Quotas

| Quota ID | Description | Default | Maximum Increase To |
|----------|-------------|---------|---------------------|
| alb_quota_max_request_timeout | Maximum connection request timeout | 600s | 3600s (upgraded instance) / 900s (not upgraded) |
| alb_quota_max_idle_timeout | Maximum connection idle timeout | 600s | 3600s (upgraded instance) / 900s (not upgraded) |

#### Server Group Quotas

| Quota ID | Description | Default | Maximum Increase To |
|----------|-------------|---------|---------------------|
| alb_quota_server_added_num | Number of times the same backend server (IP) can be added to server groups | 200 | 300 |
| alb_quota_servergroup_attached_num | Number of times the same server group can be associated with listeners and forwarding rules | 50 | 100 |
| alb_quota_server_groups_weight | Upper limit of weight configurable for a single server group when a forwarding rule forwards to it | 100 | 10000 (contact sales) |

#### Resource Reservation Quotas

| Quota ID | Description | Default |
|----------|-------------|---------|
| alb_quota_reserved_capacity_units_per_loadbalancer | Maximum configurable resource reservation LCU capacity per ALB instance | 5000 (contact sales) |
| alb_quota_reserved_capacity_units_per_region | Maximum reservable LCU capacity per region | 20000 (contact sales) |

### Quota-Related Diagnosis Key Points

- **Quota exceeding does not self-heal**: Controller executes additions before deletions in a single reconcile; when quota is exceeded, additions are blocked, and subsequent deletions cannot execute either
- **alb_quota_server_added_num (default 200)**: Counting method is that each time the same backend server (IP) is referenced by a forwarding rule, the count increases by 1; multiple Ingresses referencing the same Service causes the count to multiply
- **alb_quota_loadbalancer_rules_num (Standard edition default 100)**: Forwarding rule count does not include the default rule; Standard edition can be increased to a maximum of 200
- **Significant difference between Basic and Standard editions**: Basic edition has only 40 forwarding rules (max 100), only 10 certificates (max 150), only 200 backend servers (max 400); does not support Ingress Controller management
- **Applying for quota increase**: Increase in the "Application Load Balancer ALB" tab of Alibaba Cloud Quota Center, or apply on the quota management page of the Load Balancing console. Quotas that cannot be adjusted are recommended to be evaluated via a support ticket
- **Quota alerts**: Supports creating alerts for key quotas (forwarding rules, certificates, servers, listeners, etc.), sending notifications when usage reaches the threshold

---

## Naming Conventions

- AlbConfig/Ingress/Service/Namespace names **must not start with aliyun**
- Server group name is auto-generated from Namespace+ServiceName+Port, 2-128 characters
- Label key must not start with `aliyun` or `acs:`

---

## ALB Ingress Controller Version Changelog

> Important: ACK managed clusters created after May 2024 no longer support installing v2.12.0-aliyun.1 and lower versions. Please upgrade to the latest version in a timely manner.

### Key Version Milestones

| Version | Date | Important Changes |
|---------|------|-------------------|
| **v2.19.1** | 2026-02-12 | Optimized OpenAPI rate limiting auto-retry; supported empty Tag Value; fixed ReadinessGate retry issue |
| **v2.19.0** | 2026-01-07 | Secret hot-reload defaultCertificate; supported rate limiting + fixed response / redirect + forward-to combined action; enhanced Webhook validation (SourceIP format / AclType value / backend missing port); fixed tags field deletion not clearing labels |
| **v2.18.0-aliyun.1** | 2025-07-04 | **Enabled instance managed mode by default** (new ALB cannot modify listeners in console); supported AlbConfig defaultCertificate; optimized forwarding rule priority sorting (removed global unique order); fixed HTTPS+QUIC shared port ACL issue |
| **v2.17.2-aliyun.1** | 2025-03-31 | Fixed server group reconcile error for same-name Service with different ports across multiple Namespaces; fixed IPv6 dual-stack query parameter error |
| **v2.17.1-aliyun.1** | 2025-03-18 | Supported Gateway API 1.1.0+ |
| **v2.16.0-aliyun.1** | 2025-03-04 | **New server groups enable backend persistent connection by default**; supported listener custom tags; supported disabling server group cross-AZ; Canary requires splitting into two Ingresses |
| **v2.15.2-aliyun.1** | 2025-01-24 | Supported XForwardedForProcessingMode/XForwardedForHostEnabled; fixed component unable to start when Webhook does not exist |
| **v2.15.0-aliyun.1** | 2025-01-06 | **Enabled ValidatingWebhook pre-check by default**; supported AScript; rate limiting supports fixed response; **session affinity supports custom Cookie**; compatible with ssl-redirect and rate limiting used simultaneously; fixed creator tag feature compatibility issue |
| **v2.14.1-aliyun.1** | 2024-10-12 | Fixed HTTPS health check failure |
| **v2.14.0-aliyun.1** | 2024-09-10 | Health check supports gRPC; supported slow start; supported connection graceful shutdown; supported session affinity across server groups |
| **v2.13.2-aliyun.1** | 2024-07-23 | Fixed AlbConfig format error causing Controller crash; fixed ECS/ECI mixed mount weight error under Flannel |
| **v2.13.1-aliyun.1** | 2024-05-10 | Added event when AlbConfig has no Ingress association; fixed endpoint update weight incorrect under Flannel |
| **v2.12.0-aliyun.1** | 2024-02-05 | Supported IP type server group; supported specifying server group resource group; Flannel Node auto-weights by Pod count; custom forwarding rule supports QPS rate limiting; supported X-Forwarded-For trusted IP |
| **v2.11.1-aliyun.1** | 2023-11-20 | Fixed Controller crash caused by unspecified IngressClass |
| **v2.11.0-aliyun.1** | 2023-10-31 | **No longer auto-updates AlbConfig ports, must manually specify listeners**; supported source IP rate limiting; supported tracing; supported mutual TLS; optimized multi-page certificates; prohibited deleting listeners that still have Ingress association |
| **v2.10.0-aliyun.1** | 2023-08-15 | Added hash value to prevent accidental changes on Controller restart; optimized exception event exposure |
| **v2.9.0-aliyun.1** | 2023-07-11 | Service concurrent reconcile to avoid API rate limiting; ssl-redirect optimization; certificate auto-discovery filters national cryptography versions |
| **v2.8.3-aliyun.1** | 2023-06-05 | Fixed Server reconcile not retrying; fixed custom forwarding rule Key becoming ineffective |
| **v2.8.2-aliyun.1** | 2023-05-25 | Fixed Pod restart potentially deleting forwarding rules; temporarily disabled network type update |
| **v2.8.1-aliyun.1** | 2023-05-09 | Managed component multi-replica high availability; supported use-regex; supported single availability zone; supported shared bandwidth package; supported updating instance network type |
| **v2.7.0-aliyun.1** | 2023-03-14 | Optimized reconcile flow and rule priority; supported direct ACL resource ID association; supported HTTPS+QUIC same port; Secret certificate priority higher than AlbConfig |
| **v2.6.0-aliyun.1** | 2022-12-23 | Supported ALB resource custom tags; fixed Ingress deletion blocking |
| **v2.5.0-aliyun.1** | 2022-11-23 | Supported Secret certificate upload; supported custom Header/Cookie; ACL whitelist |
| **v2.4.0-aliyun.1** | 2022-08-10 | Supported cross-origin CORS; supported backend server persistent connection |
| **v2.3.0-aliyun.1** | 2022-06-23 | Supported WAF protection; supported replacing server group load balancing algorithm |
| **v2.2.0-aliyun.1** | 2022-04-13 | Supported Rewrite; supported TCP health check; supported TLS security policy |

### Version Compatibility Diagnosis Key Points

- **v2.11.0+ (from 2023-10)**: No longer auto-creates listeners; AlbConfig must manually define all listeners. If you encounter `listener is not exist` error after upgrading from a lower version, you need to add listener configuration in AlbConfig
- **v2.15.0+ (from 2025-01)**: ValidatingWebhook pre-check is enabled by default, which intercepts configuration errors at apply time. If you encounter Webhook rejection errors, it means the configuration itself has issues
- **v2.15.0+ (from 2025-01)**: Supports Server mode custom Cookie. Versions below this using `sticky-session-type: Server` + `cookie` annotation will report `invalid server group Cookie`
- **v2.16.0+ (from 2025-03)**: New server groups enable persistent connection by default. Canary no longer supports direct annotation method and must be split into two Ingresses
- **v2.18.0+ (from 2025-07)**: Instance managed mode is enabled by default; listeners and forwarding rules of newly created ALB instances cannot be manually modified in the ALB console. Existing instances and reused instances are not affected
- **v2.12.0 and below**: ACK managed clusters created after May 2024 no longer support installation; upgrade required
