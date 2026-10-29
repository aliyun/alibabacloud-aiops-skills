# Backend Resource and Certificate Auto-Discovery Reference

This document describes how to automatically discover candidate backend resources and SSL certificates for GA endpoints, reducing manual input errors.

---

## 1. Backend Resource Discovery Flow

```
Input target region + resource type (ECS/SLB/NLB/ENI)
    │
    ├─ ECS → call ecs DescribeInstances
    ├─ SLB → call slb DescribeLoadBalancers
    ├─ NLB → call nlb ListLoadBalancers
    ├─ ENI → call ecs DescribeNetworkInterfaces
    └─ Return candidate list for user selection
```

---

## 2. Discover ECS Instances

```bash
REGION="cn-hangzhou"

aliyun ecs describe-instances \
  --biz-region-id "$REGION" \
  --page-size 50 \
  --instance-network-type vpc | jq '.Instances.Instance[] | {
    InstanceId,
    InstanceName,
    EipAddress,
    VpcAttributes: .VpcAttributes.PrivateIpAddress.IpAddress[0],
    Status
  }'
```

### As GA Endpoints

| Scenario | Endpoint Type | Endpoint Value |
|---|---|---|
| ECS public IP | Ip | ECS public IP |
| ECS private IP | Ip | ECS private IP (ensure VPC reachability) |
| ECS ENI | Eni | Elastic network interface ID |

---

## 3. Discover SLB Instances

```bash
aliyun slb describe-load-balancers \
  --biz-region-id "$REGION" \
  --page-size 50 | jq '.LoadBalancers.LoadBalancer[] | {
    LoadBalancerId,
    LoadBalancerName,
    LoadBalancerStatus,
    Address,
    AddressType
  }'
```

### As GA Endpoints

```bash
SLB_ID="lb-bp1xxxx"

aliyun slb describe-load-balancer-attribute \
  --load-balancer-id "$SLB_ID" | jq '{
    LoadBalancerId,
    Address,
    VSwitchId
  }'
```

Endpoint configuration:

```bash
--endpoint-configurations Type=Slb Endpoint="$SLB_ID"
```

---

## 4. Discover NLB Instances

```bash
aliyun nlb list-load-balancers \
  --biz-region-id "$REGION" \
  --max-results 50 | jq '.LoadBalancers[] | {
    LoadBalancerId,
    LoadBalancerName,
    LoadBalancerStatus,
    AddressIpVersion
  }'
```

Endpoint configuration:

```bash
--endpoint-configurations Type=Slb Endpoint="$NLB_ID"
```

> In GA, NLB is often mapped to endpoint type `Slb` or `Nlb`; confirm with the API documentation.

---

## 5. Discover ENIs

```bash
aliyun ecs describe-network-interfaces \
  --biz-region-id "$REGION" \
  --page-size 50 | jq '.NetworkInterfaceSets.NetworkInterfaceSet[] | {
    NetworkInterfaceId,
    NetworkInterfaceName,
    PrimaryIpAddress,
    InstanceId,
    Status
  }'
```

Endpoint configuration:

```bash
--endpoint-configurations Type=Eni Endpoint="$ENI_ID" EndpointSubAddress="$PRIMARY_IP"
```

---

## 6. Unified Discovery Script

```bash
#!/bin/bash
REGION="${1:?Please provide region ID}"
RESOURCE_TYPE="${2:?Please provide resource type: ecs|slb|nlb|eni}"

echo "=== Discovering $RESOURCE_TYPE resources in $REGION ==="

case "$RESOURCE_TYPE" in
  ecs)
    aliyun ecs describe-instances \
      --biz-region-id "$REGION" \
      --page-size 50 \
      --instance-network-type vpc | jq '.Instances.Instance[] | {
        Id: .InstanceId,
        Name: .InstanceName,
        Address: (.VpcAttributes.PrivateIpAddress.IpAddress[0]),
        Status: .Status
      }'
    ;;
  slb)
    aliyun slb describe-load-balancers \
      --biz-region-id "$REGION" \
      --page-size 50 | jq '.LoadBalancers.LoadBalancer[] | {
        Id: .LoadBalancerId,
        Name: .LoadBalancerName,
        Address: .Address,
        Status: .LoadBalancerStatus
      }'
    ;;
  nlb)
    aliyun nlb list-load-balancers \
      --biz-region-id "$REGION" \
      --max-results 50 | jq '.LoadBalancers[] | {
        Id: .LoadBalancerId,
        Name: .LoadBalancerName,
        Status: .LoadBalancerStatus
      }'
    ;;
  eni)
    aliyun ecs describe-network-interfaces \
      --biz-region-id "$REGION" \
      --page-size 50 | jq '.NetworkInterfaceSets.NetworkInterfaceSet[] | {
        Id: .NetworkInterfaceId,
        Name: .NetworkInterfaceName,
        Address: .PrimaryIpAddress,
        InstanceId: (.InstanceId // "unbound"),
        Status: .Status
      }'
    ;;
  *)
    echo "Unsupported resource type: $RESOURCE_TYPE"
    exit 1
    ;;
esac
```

---

## 7. SSL Certificate Auto-Discovery

> **Verified CLI contract**: use `cas list-certificates` to discover GA-usable certificates. It returns `CertificateList[]` with `CertificateId`, `CertIdentifier` (already `<id>-<region>`), `CertificateName`, `CommonName`, `CertificateStatus` and `NotAfter` (epoch ms). Pagination flags are `--current-page` / `--show-size` (default 50); `--page-size` is rejected. `cas list-user-certificate-order` returns sell-order records (OrderId/InstanceId) and, in practice, **does not carry `CertificateId`**, so it cannot be used to build a GA certificate ID — use it only for order details.

### List valid certificates

```bash
aliyun cas list-certificates \
  --region cn-hangzhou \
  --current-page 1 \
  --show-size 50 \
  --user-agent "$GA_USER_AGENT" | jq '.CertificateList[] | {
    CertificateId,
    CertIdentifier,
    CertificateName,
    CommonName,
    CertificateStatus,
    NotAfter
  }'
```

### Shortlist by remaining validity

```bash
NOW_MS=$(date +%s000)
aliyun cas list-certificates \
  --region cn-hangzhou --current-page 1 --show-size 50 \
  --user-agent "$GA_USER_AGENT" \
| jq --argjson now "$NOW_MS" '
  [.CertificateList[]?
   | select(.NotAfter > $now)
   | {CertificateId, CertIdentifier, CommonName, NotAfter,
      RemainingDays: (((.NotAfter - $now) / 86400000) | floor)}]
  | sort_by(-.RemainingDays)'
```

### Filter certificates by domain

```bash
DOMAIN="example.com"

aliyun cas list-certificates \
  --region cn-hangzhou \
  --current-page 1 \
  --show-size 50 \
  --user-agent "$GA_USER_AGENT" | jq --arg domain "$DOMAIN" '
    .CertificateList[]?
    | select(((.CommonName // "") | contains($domain)) or ((.Domain // "") | contains($domain)))
    | {CertificateId, CertIdentifier, CommonName, NotAfter}'
```

Uploaded certificates usually have a null `Domain` field — match on `CommonName` for them.

### GA certificate ID format (critical)

GA listeners do **not** accept the raw numeric CAS `CertificateId`. Pass the region-suffixed form, which `list-certificates` already exposes as `CertIdentifier`:

```
<CertificateId>-<region>      # e.g. 26311018-cn-hangzhou
```

Use it in Step 4 as `--certificates Id=<CertIdentifier>`. Never invent a bare numeric ID.

### One-shot discovery script

`scripts/ga-discover-certificate.sh` prints valid certificates with remaining days and the GA-ready `GaCertificateId`:

```bash
bash scripts/ga-discover-certificate.sh                        # all valid certs
bash scripts/ga-discover-certificate.sh --domain example.com   # filter by domain
```

### Recommend the best matching certificate

1. Prefer a certificate whose `CommonName` (or `Domain`) matches the listener domain; wildcards count.
2. Among matches, pick the **longest remaining validity** (`CertEndTime` farthest in the future).
3. Report the chosen certificate's domain, expiry date, and the exact GA certificate ID before creating the listener; ask the user to confirm if several certificates match equally.

---

## 8. Skill Integration Notes

During Step 3 (create endpoint group), when asking for endpoints, add an auto-discovery option:

```
Question: How do you want to specify the endpoint?
- Option 1: Manual input (default)
- Option 2: Auto-discover ECS in the current region
- Option 3: Auto-discover SLB in the current region
- Option 4: Auto-discover NLB in the current region
- Option 5: Auto-discover ENI in the current region

If auto-discovery is selected:
1. Call the corresponding cloud product query API.
2. List candidates (ID, name, IP, status).
3. Let the user select the target resource.
4. Auto-fill EndpointConfigurations.
```

During Step 4 (create HTTPS listener), when asking for the SSL certificate, add an auto-discovery option:

```
Question: How do you want to specify the SSL certificate?
- Option 1: Manual input of certificate ID
- Option 2: Auto-discover certificates matching the domain

If auto-discovery is selected:
1. Ask for the domain or service name.
2. Run `scripts/ga-discover-certificate.sh --domain <domain>` (wraps `cas list-certificates`).
3. Filter by domain and list candidate certificates.
4. Recommend the certificate with the longest remaining validity.
5. Use the selected `CertIdentifier` (already `<CertificateId>-<region>`) as the GA certificate ID.
```

---

## 9. Notes

1. Auto-discovery requires additional RAM permissions such as `ecs:DescribeInstances`, `slb:DescribeLoadBalancers`, `nlb:ListLoadBalancers`, and `cas:ListCertificates`.
2. When using private IPs or ENIs as endpoints, ensure GA can reach the target VPC.
3. Classic SLB and NLB may differ in GA usage; prefer VPC-type SLB or NLB.
4. When recommending certificates, prefer the one with the longest remaining validity and remind the user of the expiration date.
5. `cas` pagination uses `--current-page` / `--show-size`; `--page-size` is rejected. Use `list-certificates` for GA-usable certificates.
