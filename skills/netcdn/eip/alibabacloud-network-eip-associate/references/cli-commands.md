# EIP CLI Command Reference

## Check if resource has EIP bound
```bash
aliyun vpc describe-eip-addresses \
  --biz-region-id cn-beijing \
  --associated-instance-type EcsInstance \
  --associated-instance-id i-bp1xxx \
  --user-agent AlibabaCloud-Agent-Skills
```

## Check if ECS has Public IP (PIP)
```bash
aliyun ecs describe-instance-attribute \
  --instance-id i-bp1xxx \
  --user-agent AlibabaCloud-Agent-Skills
```
Check `PublicIpAddress.IpAddress` field in response:
- If not empty: ECS has PIP, cannot bind EIP
- If empty: No PIP, can bind EIP

## Allocate EIP
```bash
aliyun vpc allocate-eip-address \
  --biz-region-id cn-beijing \
  --bandwidth 5 \
  --isp BGP \
  --internet-charge-type PayByTraffic \
  [--name "my-eip"] \
  --user-agent AlibabaCloud-Agent-Skills
```

## Bind EIP to ECS
```bash
aliyun vpc associate-eip-address \
  --biz-region-id cn-beijing \
  --allocation-id eip-bp1xxx \
  --instance-id i-bp1yyy \
  --instance-type EcsInstance \
  --user-agent AlibabaCloud-Agent-Skills
```

## Bind EIP to ENI (requires PrivateIpAddress)
```bash
aliyun vpc associate-eip-address \
  --biz-region-id cn-beijing \
  --allocation-id eip-bp1xxx \
  --instance-id eni-bp1zzz \
  --instance-type NetworkInterface \
  --private-ip-address 192.168.1.10 \
  --user-agent AlibabaCloud-Agent-Skills
```

## Bind EIP to IP Address (requires VpcId)
```bash
aliyun vpc associate-eip-address \
  --biz-region-id cn-beijing \
  --allocation-id eip-bp1xxx \
  --instance-id 192.168.1.100 \
  --instance-type IpAddress \
  --vpc-id vpc-bp1www \
  --user-agent AlibabaCloud-Agent-Skills
```

## Query EIP Status
```bash
aliyun vpc describe-eip-addresses \
  --biz-region-id cn-beijing \
  --allocation-id eip-bp1xxx \
  --user-agent AlibabaCloud-Agent-Skills
```

## Unbind EIP
```bash
aliyun vpc unassociate-eip-address \
  --biz-region-id cn-beijing \
  --allocation-id eip-bp1xxx \
  --instance-id i-bp1yyy \
  --instance-type EcsInstance \
  --user-agent AlibabaCloud-Agent-Skills
```

## Release EIP
```bash
aliyun vpc release-eip-address \
  --biz-region-id cn-beijing \
  --allocation-id eip-bp1xxx \
  --user-agent AlibabaCloud-Agent-Skills
```
