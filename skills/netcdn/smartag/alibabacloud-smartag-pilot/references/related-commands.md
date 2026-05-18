# Related Commands: alibabacloud-smartag-pilot

All CLI commands used by this skill. Uses CLI plugin mode (aliyun-cli-smartag) with kebab-case API and parameter names.

---

## Command Template

```bash
aliyun smartag <api-name-in-kebab-case> \
  --endpoint smartag.<RegionId>.aliyuncs.com \
  --biz-region-id <RegionId> \
  --read-timeout 30 \
  --connect-timeout 15 \
  [--other-params ...]
```

---

## Region Discovery

| Plugin API | Description | Key Parameters |
|-----------|-------------|---------------|
| describe-regions | List all SAG-available regions | --endpoint (not --biz-region-id) |

---

## Configuration Query Commands

| # | Plugin API | Description | Key Parameters |
|---|-----------|-------------|----------------|
| 1 | describe-smart-access-gateways | List instances (paginated) | --biz-region-id, --page-size, --page-number |
| 1 | describe-smart-access-gateway-attribute | Single instance detail | --smart-ag-id, --biz-region-id |
| 2 | describe-sag-device-info | Device hardware info | --smart-ag-id, --smart-ag-sn |
| 2 | describe-smart-access-gateway-versions | Software versions | --smart-ag-id, --biz-region-id |
| 3 | describe-sag-wan-list | WAN port list | --smart-ag-id, --smart-ag-sn |
| 3 | describe-sag-wan-4g | 4G link status | --smart-ag-id, --smart-ag-sn |
| 4 | describe-sag-static-route-list | Static routes | --smart-ag-id, --smart-ag-sn |
| 4 | describe-sag-route-list | Route table | --smart-ag-id, --smart-ag-sn, --biz-region-id |
| 4 | describe-sag-route-protocol-bgp | BGP config | --smart-ag-id, --smart-ag-sn, --biz-region-id |
| 4 | describe-sag-route-protocol-ospf | OSPF config | --smart-ag-id, --smart-ag-sn, --biz-region-id |
| 5 | describe-cloud-connect-networks | CCN list (region-level) | --biz-region-id, --page-size |
| 5 | describe-grant-sag-rules | CEN authorization rules | --smart-ag-id, --biz-region-id, --page-size |
| 5 | describe-sag-vbr-relations | VBR relations | --smart-ag-id, --biz-region-id |
| 6 | describe-acls | ACL list (region-level) | --biz-region-id, --page-size |
| 7 | describe-qoses | QoS list (region-level) | --biz-region-id, --page-size |
| 8 | describe-dnat-entries | DNAT rules | **--sag-id** (not --smart-ag-id), --biz-region-id |
| 8 | describe-snat-entries | SNAT rules | --smart-ag-id, --biz-region-id |
| 9 | describe-flow-logs | Flow log config (region-level) | --biz-region-id, --page-size |
| 10 | describe-health-checks | Health check probes | --smart-ag-id, --biz-region-id |
| 10 | describe-health-check-attribute | Health check detail | --hc-instance-id, --biz-region-id |
| 11 | describe-smart-access-gateway-client-users | APP client users | --smart-ag-id, --biz-region-id, --page-size |
| 11 | describe-sag-online-client-statistics | Online client stats | --smart-ag-id, --biz-region-id |
| 12 | describe-sag-current-dns | DNS servers | --smart-ag-id, --smart-ag-sn, --biz-region-id |

---

## Status Inspection Commands (状态巡检)

| # | Plugin API | Description | Key Parameters (plugin) |
|---|-----------|-------------|------------------------|
| 1 | describe-smart-access-gateways | Check Status field | --biz-region-id, --smart-ag-id |
| 2 | describe-smart-access-gateway-attribute | Check VPN tunnel status | --smart-ag-id |
| 3 | describe-smart-access-gateway-ha | HA status | --smart-ag-id, --biz-region-id |
| 4 | describe-smart-access-gateways | Check EndTime for expiry | --smart-ag-id |
| 5 | describe-sag-wan-4g | 4G signal strength | --smart-ag-id, --smart-ag-sn |
| 6 | describe-grant-sag-rules | CCN/CEN binding chain | --smart-ag-id, --biz-region-id |
| 7 | describe-sag-route-list | Route table health | --smart-ag-id, --smart-ag-sn |
| 8 | describe-acls | ACL binding sanity | --biz-region-id |
| 9 | describe-flow-logs | Flow log enablement | --biz-region-id |

---

## Parameter Traps

| Plugin Command | Trap | Correct Usage |
|---------------|------|---------------|
| describe-dnat-entries | Instance ID param name differs | Use `--sag-id` (not `--smart-ag-id`) |
| Device-level APIs (#2,3,4,12) | Require device serial number | Must pass `--smart-ag-sn` |
| Device-level APIs with HA | Multi-SN in comma-separated field | Split and query each SN individually |
