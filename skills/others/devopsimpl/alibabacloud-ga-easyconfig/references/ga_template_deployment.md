# Template-Based Batch Deployment Reference

This document describes how to deploy GA resources from JSON templates, suitable for standardized, multi-environment, and repeatable deployments.

> **Important**: Template deployment is intended for users already familiar with GA. First-time users should follow the guided step-by-step workflow.

---

## 1. Template File Specifications

### 1.1 Standard Accelerator Template

Suggested filename: `ga-template-standard.json`

```json
{
  "template_version": "1.0",
  "instance_type": "Standard",
  "accelerator": {
    "name": "ga-standard-prod",
    "instance_charge_type": "POSTPAY",
    "bandwidth_billing_type": "CDT",
    "ip_set_config": {
      "access_mode": "UserDefine"
    }
  },
  "bandwidth_packages": [],
  "ip_sets": [
    {
      "accelerate_region_id": "cn-beijing",
      "bandwidth": 5,
      "ip_version": "IPv4",
      "isp_type": "BGP"
    },
    {
      "accelerate_region_id": "us-west-1",
      "bandwidth": 3,
      "ip_version": "IPv4",
      "isp_type": "BGP"
    }
  ],
  "listeners": [
    {
      "name": "listener-tcp-80",
      "protocol": "TCP",
      "port_ranges": [{"from_port": 80, "to_port": 80}],
      "type": "Standard",
      "client_affinity": "SOURCE_IP",
      "endpoint_groups": [
        {
          "endpoint_group_region": "cn-hangzhou",
          "traffic_percentage": 100,
          "health_check": {
            "enabled": true,
            "protocol": "TCP",
            "port": 80,
            "interval_seconds": 10,
            "threshold_count": 3
          },
          "endpoints": [
            {
              "type": "Ip",
              "endpoint": "47.xxx.xxx.xxx",
              "weight": 255,
              "enable_client_ip_preservation": true
            }
          ]
        }
      ]
    }
  ]
}
```

### 1.2 Basic Accelerator Template

Suggested filename: `ga-template-basic.json`

```json
{
  "template_version": "1.0",
  "instance_type": "Basic",
  "accelerator": {
    "name": "ga-basic-prod",
    "charge_type": "POSTPAY",
    "bandwidth_billing_type": "CDT"
  },
  "ip_set": {
    "accelerate_region_id": "cn-shanghai",
    "bandwidth": 2,
    "isp_type": "BGP"
  },
  "endpoint_group": {
    "endpoint_group_region": "cn-hangzhou",
    "name": "basic-epg",
    "endpoint_type": "ENI",
    "endpoint_address": "eni-bp1xxxx"
  },
  "endpoints": [
    {
      "name": "ep-01",
      "endpoint_type": "ENI",
      "endpoint_address": "eni-bp1xxxx",
      "endpoint_sub_address": "172.16.1.10",
      "endpoint_sub_address_type": "primary"
    }
  ]
}
```

---

## 2. Standard Accelerator Template Deployment Script

```bash
#!/bin/bash
TEMPLATE="${1:?Please provide template file, usage: bash deploy_template.sh <template.json>}"
REGION="cn-hangzhou"

echo "=== Reading template: $TEMPLATE ==="
CONFIG=$(cat "$TEMPLATE")
INSTANCE_TYPE=$(echo "$CONFIG" | jq -r '.instance_type')

if [ "$INSTANCE_TYPE" != "Standard" ]; then
  echo "This script supports only Standard accelerator templates. Use deploy_basic_template.sh for Basic accelerators."
  exit 1
fi

# Step 1: Create accelerator
GA_NAME=$(echo "$CONFIG" | jq -r '.accelerator.name')
CHARGE_TYPE=$(echo "$CONFIG" | jq -r '.accelerator.instance_charge_type')
BILLING_TYPE=$(echo "$CONFIG" | jq -r '.accelerator.bandwidth_billing_type')
ACCESS_MODE=$(echo "$CONFIG" | jq -r '.accelerator.ip_set_config.access_mode // "UserDefine"')

echo "Creating Standard GA accelerator..."
GA_RESULT=$(aliyun ga create-accelerator  --user-agent "$GA_USER_AGENT" \
  --biz-region-id "$REGION" \
  --name "$GA_NAME" \
  --instance-charge-type "$CHARGE_TYPE" \
  --bandwidth-billing-type "$BILLING_TYPE" \
  --ip-set-config AccessMode="$ACCESS_MODE" \
  --auto-pay true)

GA_ID=$(echo "$GA_RESULT" | jq -r '.AcceleratorId')
echo "Accelerator ID: $GA_ID"

# Wait for accelerator to become active
for i in $(seq 1 30); do
  STATE=$(aliyun ga describe-accelerator --biz-region-id "$REGION" --accelerator-id "$GA_ID" --user-agent "$GA_USER_AGENT" | jq -r '.State')
  [ "$STATE" = "active" ] && break
  echo "Waiting for accelerator... [$i/30] state: $STATE"
  sleep 10
done

# Step 2: Create acceleration regions
IP_SET_COUNT=$(echo "$CONFIG" | jq '.ip_sets | length')
if [ "$IP_SET_COUNT" -gt 0 ]; then
  echo "Creating acceleration regions..."
  ACCELERATE_REGIONS=$(echo "$CONFIG" | jq -c '[.ip_sets[] | {
    AccelerateRegionId: .accelerate_region_id,
    Bandwidth: (.bandwidth | tonumber),
    IpVersion: (.ip_version // "IPv4"),
    IspType: (.isp_type // "BGP")
  }]')
  aliyun ga create-ip-sets \
    --biz-region-id "$REGION" \
    --accelerator-id "$GA_ID" \
    --accelerate-region "$ACCELERATE_REGIONS" \
    --user-agent "$GA_USER_AGENT"
  sleep 15
fi

# Step 3: Create listeners and endpoint groups
LISTENER_COUNT=$(echo "$CONFIG" | jq '.listeners | length')
for i in $(seq 0 $((LISTENER_COUNT - 1))); do
  L=$(echo "$CONFIG" | jq ".listeners[$i]")
  PROTOCOL=$(echo "$L" | jq -r '.protocol')
  L_NAME=$(echo "$L" | jq -r '.name')
  TYPE=$(echo "$L" | jq -r '.type // "Standard"')
  CLIENT_AFFINITY=$(echo "$L" | jq -r '.client_affinity // "SOURCE_IP"')

  echo "Creating listener: $L_NAME ..."

  PORT_RANGES=$(echo "$L" | jq -c '[.port_ranges[] | {FromPort: (.from_port | tonumber), ToPort: (.to_port | tonumber)}]')

  LISTENER_RESULT=$(aliyun ga create-listener \
    --biz-region-id "$REGION" \
    --accelerator-id "$GA_ID" \
    --name "$L_NAME" \
    --protocol "$PROTOCOL" \
    --port-ranges "$PORT_RANGES" \
    --type "$TYPE" \
    --client-affinity "$CLIENT_AFFINITY" \
    --user-agent "$GA_USER_AGENT")

  LISTENER_ID=$(echo "$LISTENER_RESULT" | jq -r '.ListenerId')
  echo "Listener ID: $LISTENER_ID"

  # Wait for listener to become active
  for k in $(seq 1 30); do
    STATE=$(aliyun ga describe-listener --biz-region-id "$REGION" --listener-id "$LISTENER_ID" --user-agent "$GA_USER_AGENT" | jq -r '.State')
    [ "$STATE" = "active" ] && break
    sleep 10
  done

  # Create endpoint groups
  EPG_COUNT=$(echo "$L" | jq '.endpoint_groups | length')
  for j in $(seq 0 $((EPG_COUNT - 1))); do
    EPG=$(echo "$L" | jq ".endpoint_groups[$j]")
    EPG_REGION=$(echo "$EPG" | jq -r '.endpoint_group_region')
    TRAFFIC_PCT=$(echo "$EPG" | jq -r '.traffic_percentage // 100')
    HC_ENABLED=$(echo "$EPG" | jq -r '.health_check.enabled // true')
    HC_PROTOCOL=$(echo "$EPG" | jq -r '.health_check.protocol // "TCP"')
    HC_PORT=$(echo "$EPG" | jq -r '.health_check.port // 80')
    HC_INTERVAL=$(echo "$EPG" | jq -r '.health_check.interval_seconds // 10')
    HC_THRESHOLD=$(echo "$EPG" | jq -r '.health_check.threshold_count // 3')

    echo "Creating endpoint group..."
    EPG_RESULT=$(aliyun ga create-endpoint-group \
      --biz-region-id "$REGION" \
      --accelerator-id "$GA_ID" \
      --listener-id "$LISTENER_ID" \
      --endpoint-group-region "$EPG_REGION" \
      --traffic-percentage "$TRAFFIC_PCT" \
      --health-check-enabled "$HC_ENABLED" \
      --health-check-protocol "$HC_PROTOCOL" \
      --health-check-port "$HC_PORT" \
      --health-check-interval-seconds "$HC_INTERVAL" \
      --threshold-count "$HC_THRESHOLD" \
      --user-agent "$GA_USER_AGENT")

    EPG_ID=$(echo "$EPG_RESULT" | jq -r '.EndpointGroupId')

    # Add endpoints (two-step flow: create group first, then update with configurations)
    ENDPOINT_CONFIGS=$(echo "$EPG" | jq -c '[.endpoints[] | {
      Type: .type,
      Endpoint: .endpoint,
      Weight: (.weight // 255),
      EnableClientIPPreservation: (.enable_client_ip_preservation // false)
    }]')

    aliyun ga update-endpoint-group \
      --biz-region-id "$REGION" \
      --endpoint-group-id "$EPG_ID" \
      --endpoint-group-region "$EPG_REGION" \
      --endpoint-configurations "$ENDPOINT_CONFIGS" \
      --user-agent "$GA_USER_AGENT"

    sleep 10
  done
done

# Save configuration
aliyun ga describe-accelerator --biz-region-id "$REGION" --accelerator-id "$GA_ID" \
--user-agent "$GA_USER_AGENT" | jq '{
  accelerator_id: .AcceleratorId,
  accelerator_name: .Name,
  instance_charge_type: .InstanceChargeType,
  bandwidth_billing_type: .BandwidthBillingType,
  dns_name: .DnsName
}' > ga-config.json

echo ""
echo "=== Template deployment complete ==="
echo "Accelerator ID: $GA_ID"
```

---

## 3. Basic Accelerator Template Deployment Script

```bash
#!/bin/bash
TEMPLATE="${1:?Please provide template file, usage: bash deploy_basic_template.sh <template.json>}"
REGION="cn-hangzhou"

CONFIG=$(cat "$TEMPLATE")
INSTANCE_TYPE=$(echo "$CONFIG" | jq -r '.instance_type')

if [ "$INSTANCE_TYPE" != "Basic" ]; then
  echo "This script supports only Basic accelerator templates."
  exit 1
fi

GA_NAME=$(echo "$CONFIG" | jq -r '.accelerator.name')
CHARGE_TYPE=$(echo "$CONFIG" | jq -r '.accelerator.charge_type')
BILLING_TYPE=$(echo "$CONFIG" | jq -r '.accelerator.bandwidth_billing_type')

echo "Creating Basic GA accelerator..."
GA_RESULT=$(aliyun ga create-basic-accelerator  --user-agent "$GA_USER_AGENT" \
  --biz-region-id "$REGION" \
  --name "$GA_NAME" \
  --charge-type "$CHARGE_TYPE" \
  --bandwidth-billing-type "$BILLING_TYPE" \
  --auto-pay true)

GA_ID=$(echo "$GA_RESULT" | jq -r '.AcceleratorId')
echo "Accelerator ID: $GA_ID"

# Wait for accelerator to become active
for i in $(seq 1 30); do
  STATE=$(aliyun ga get-basic-accelerator --biz-region-id "$REGION" --accelerator-id "$GA_ID" --user-agent "$GA_USER_AGENT" | jq -r '.State')
  [ "$STATE" = "active" ] && break
  sleep 10
done

# Create acceleration region
IP_SET=$(echo "$CONFIG" | jq '.ip_set')
ACC_REGION=$(echo "$IP_SET" | jq -r '.accelerate_region_id')
BANDWIDTH=$(echo "$IP_SET" | jq -r '.bandwidth')
ISP_TYPE=$(echo "$IP_SET" | jq -r '.isp_type // "BGP"')

IP_SET_RESULT=$(aliyun ga create-basic-ip-set \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --accelerate-region-id "$ACC_REGION" \
  --bandwidth "$BANDWIDTH" \
  --isp-type "$ISP_TYPE" \
  --user-agent "$GA_USER_AGENT")

IP_SET_ID=$(echo "$IP_SET_RESULT" | jq -r '.IpSetId')
sleep 15

# Create accelerate IP
IP_RESULT=$(aliyun ga create-basic-accelerate-ip  --user-agent "$GA_USER_AGENT" \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --ip-set-id "$IP_SET_ID")
ACCELERATE_IP_ID=$(echo "$IP_RESULT" | jq -r '.AccelerateIpId')
sleep 15

# Create endpoint group
EPG=$(echo "$CONFIG" | jq '.endpoint_group')
EPG_REGION=$(echo "$EPG" | jq -r '.endpoint_group_region')
EPG_NAME=$(echo "$EPG" | jq -r '.name')
EP_TYPE=$(echo "$EPG" | jq -r '.endpoint_type')
EP_ADDR=$(echo "$EPG" | jq -r '.endpoint_address')

EPG_RESULT=$(aliyun ga create-basic-endpoint-group \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --endpoint-group-region "$EPG_REGION" \
  --name "$EPG_NAME" \
  --endpoint-type "$EP_TYPE" \
  --endpoint-address "$EP_ADDR" \
  --user-agent "$GA_USER_AGENT")

EPG_ID=$(echo "$EPG_RESULT" | jq -r '.EndpointGroupId')
sleep 15

# Create endpoint
EP=$(echo "$CONFIG" | jq '.endpoints[0]')
EP_NAME=$(echo "$EP" | jq -r '.name')
EP_SUB_ADDR=$(echo "$EP" | jq -r '.endpoint_sub_address // empty')
EP_SUB_TYPE=$(echo "$EP" | jq -r '.endpoint_sub_address_type // empty')

EP_ARGS=""
[ -n "$EP_SUB_ADDR" ] && EP_ARGS="$EP_ARGS --endpoint-sub-address "$EP_SUB_ADDR""
[ -n "$EP_SUB_TYPE" ] && EP_ARGS="$EP_ARGS --endpoint-sub-address-type "$EP_SUB_TYPE""

EP_RESULT=$(aliyun ga create-basic-endpoint \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --endpoint-group-id "$EPG_ID" \
  --name "$EP_NAME" \
  --endpoint-type "$EP_TYPE" \
  --endpoint-address "$EP_ADDR" \
  $EP_ARGS \
  --user-agent "$GA_USER_AGENT")

ENDPOINT_ID=$(echo "$EP_RESULT" | jq -r '.EndpointId')
sleep 15

# Create binding
aliyun ga create-basic-accelerate-ip-endpoint-relation \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --accelerate-ip-id "$ACCELERATE_IP_ID" \
  --user-agent "$GA_USER_AGENT" \
  --endpoint-id "$ENDPOINT_ID"

echo ""
echo "=== Basic template deployment complete ==="
echo "Accelerator ID: $GA_ID"
```

---

## 4. Template Variable Substitution

For multi-environment deployments, use placeholders in templates and replace them before deployment:

```json
{
  "accelerator": {
    "name": "ga-{{ENV}}-app"
  }
}
```

```bash
ENV="prod"
# Whitelist the value before it reaches sed: no slashes, ampersands or other
# sed metacharacters can appear in the replacement text.
case "$ENV" in
  ''|*[!A-Za-z0-9._-]*) echo "ERROR: ENV may contain only letters, digits, dot, underscore and hyphen" >&2; exit 2 ;;
esac
sed "s/{{ENV}}/${ENV}/g" ga-template-standard.json > ga-template-rendered.json
bash deploy_template.sh ga-template-rendered.json
```

---

## 5. Multi-Environment Template Management

| File | Purpose |
|---|---|
| `ga-template-standard.json` | Standard accelerator general template |
| `ga-template-basic.json` | Basic accelerator general template |
| `ga-template-prod.json` | Production environment template |
| `ga-template-test.json` | Test environment template |
| `ga-template-rendered.json` | Rendered temporary template (do not commit to version control) |

---

## 6. Notes

1. **Idempotency**: Template deployment creates new resources; repeated execution creates duplicates. Before running, check whether the target instance already exists, and pass the deterministic `--client-token` described in `SKILL.md` (`Idempotency`) to every create call whose parameter table supports it.
2. **Error handling**: Check return codes after each API call; stop and roll back created resources on failure.
3. **Resource naming**: Use `${timestamp}` or environment variables in templates to avoid naming conflicts.
4. **PowerShell adaptation**: Windows users can replace `jq` with `ConvertFrom-Json` and use `foreach` loops.
