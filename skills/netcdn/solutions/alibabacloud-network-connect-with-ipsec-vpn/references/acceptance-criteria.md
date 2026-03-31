# Acceptance Criteria: alibabacloud-network-connect-using-ipsec

**Scenario**: Linux Server Connecting to Alibaba Cloud VPC via IPsec VPN
**Purpose**: Skill testing and acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — All commands use `vpc` product

#### ✅ CORRECT
```bash
aliyun vpc create-vpn-gateway ...
aliyun vpc create-customer-gateway ...
aliyun vpc create-vpn-connection ...
```

#### ❌ INCORRECT
```bash
aliyun vpn create-gateway ...       # Wrong product name, should be vpc
aliyun vpc CreateVpnGateway ...     # Using traditional API format, should be plugin mode
```

## 2. Command — All commands use plugin mode (lowercase-with-hyphens format)

#### ✅ CORRECT
```bash
aliyun vpc create-vpn-gateway
aliyun vpc create-customer-gateway
aliyun vpc create-vpn-connection
aliyun vpc describe-vpn-gateway
aliyun vpc describe-vpn-gateways
aliyun vpc describe-vpn-connections
aliyun vpc describe-vpn-connection-logs
aliyun vpc diagnose-vpn-connections
aliyun vpc delete-vpn-connection
aliyun vpc delete-customer-gateway
aliyun vpc delete-vpn-gateway
aliyun vpc download-vpn-connection-config
```

#### ❌ INCORRECT
```bash
aliyun vpc CreateVpnGateway          # Traditional API format
aliyun vpc DescribeVpnGateways       # Traditional API format
aliyun vpc CreateVpnConnection       # Traditional API format
aliyun vpc CreateCustomerGateway     # Traditional API format
```

## 3. Parameters — Use plugin mode parameter format

#### ✅ CORRECT
```bash
# Plugin mode parameter format (lowercase with hyphens)
aliyun vpc create-vpn-gateway \
  --region cn-beijing \
  --biz-region-id cn-beijing \
  --vpc-id vpc-xxx \
  --bandwidth 10 \
  --vswitch-id vsw-xxx \
  --disaster-recovery-vswitch-id vsw-yyy \
  --instance-charge-type PREPAY \
  --period 1 \
  --auto-pay true \
  --enable-ipsec true \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Traditional API parameter format
aliyun vpc CreateVpnGateway \
  --RegionId cn-beijing \
  --VpcId vpc-xxx \
  --Bandwidth 10 \
  --VSwitchId vsw-xxx \
  --DisasterRecoveryVSwitchId vsw-yyy
```

## 4. Region Parameter — Use --region && --biz-region-id

#### ✅ CORRECT
```bash
aliyun vpc create-vpn-gateway --region cn-beijing --biz-region-id cn-beijing ...
aliyun vpc describe-vpn-gateways --region cn-hangzhou --biz-region-id cn-hangzhou ...
```

#### ❌ INCORRECT
```bash
aliyun vpc create-vpn-gateway --RegionId cn-beijing ...  # Traditional param name
```

## 5. user-agent Tag — Must be included in every command

#### ✅ CORRECT
```bash
aliyun vpc describe-vpn-gateways \
  --region cn-beijing --biz-region-id cn-beijing \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
aliyun vpc describe-vpn-gateways \
  --region cn-beijing --biz-region-id cn-beijing 
  # Missing --user-agent AlibabaCloud-Agent-Skills
```

## 6. StrongSwan Configuration — IKE/IPsec params must match Aliyun side exactly

#### ✅ CORRECT
```conf
# StrongSwan swanctl.conf (VICI method)
connections {
   aliyun-vpn-master {
      version = 2
      proposals = aes256-sha256-modp2048
      local { auth = psk }
      remote { auth = psk }
      children {
         aliyun-vpn-master-child {
            esp_proposals = aes256-sha256-modp2048
            life_time = 86400s
            priority = 100
         }
      }
   }
}
```
Corresponding Aliyun side:
- IkeVersion=ikev2, IkeEncAlg=aes256, IkeAuthAlg=sha256, IkePfs=group14
- IpsecEncAlg=aes256, IpsecAuthAlg=sha256, IpsecPfs=group14

#### ❌ INCORRECT
```conf
# Inconsistent parameters
connections {
   aliyun-vpn-master {
      version = 1               # Should be 2 (ikev2)
      proposals = aes128-sha1-modp1024  # Encryption algorithm mismatch
      children {
         aliyun-vpn-master-child {
            esp_proposals = aes128-sha1   # Encryption algorithm mismatch
         }
      }
   }
}
```

## 7. Security Checks

#### ✅ CORRECT
- Use `aliyun configure list` to check credential status
- PSK uses randomly generated strong password
- No hard-coded user-specific parameters

#### ❌ INCORRECT
- Using `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` to print credentials
- Hard-coding PSK password as "password123"
- Hard-coding region "cn-beijing" without user confirmation
