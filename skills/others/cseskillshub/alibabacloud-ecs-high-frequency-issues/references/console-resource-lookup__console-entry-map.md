# Console entry map (verified links and paths only)

Every URL below was actually used by a support agent in a real ticket of this
tier and recorded in the requirements analysis (section 4.2). The rule for
this skill is strict: **only these URLs may be quoted; an entry path that is
not in this file or in `scripts/areas/console_resource_lookup/console_navigation.py` output must be
described as "locate it in the console menu" or escalated, never invented.**
Signature-bearing temporary links, image-host links and tracking parameters
from the ticket dialogs are deliberately excluded.

Machine-readable copy: the `ENTRY_MAP` / `OFFICIAL_DOCS` constants in
`scripts/areas/console_resource_lookup/_constants.py`; quote the scripts' output rather than retyping URLs.

## ECS console pages (region-scoped unless noted)

| Target | Path / link | Ticket source |
|---|---|---|
| Instance list, one region at a time | https://ecs.console.aliyun.com/server/region/cn-hangzhou#/ (swap the region id) | T-69E628E3, T-804A0640 |
| Snapshot list | https://ecs.console.aliyun.com/snapshot | T-D52AE555 |
| Security groups | https://ecs.console.aliyun.com/securityGroup/region/cn-hangzhou | T-A250313A |
| Re-initialize system disk (deep menu) | instance list > More > disk and image group > re-initialize system disk; requires the instance stopped; wipes the system disk irreversibly, take a snapshot first (customer-side action) | T-69E628E3 dialog (wording drifts between "disk" and "system disk") |

## Cross-product consoles for "the entry is in another console" tickets

| Owning product | Entry | Ticket source |
|---|---|---|
| RAM (users/roles/policies) | https://ram.console.aliyun.com/overview?activeTab=overview | T-8AA82DFC |
| Billing: orders | https://billing-cost.console.aliyun.com/order/list | T-DF87AF28 |
| Billing: unsubscribe/refund self-service | https://billing-cost.console.aliyun.com/refund/refund | T-B2672FDF |
| Billing: contracts (ICP-filing server access agreement lives here) | https://billing-cost.console.aliyun.com/contract/manage | T-2000646E |
| EIP (VPC console) | https://vpc.console.aliyun.com/eip/cn-shenzhen/eips (swap region) | T-AB34E2B9 |
| DNS resolution records | https://dns.console.aliyun.com/#/dns/domainList | T-F66F330B |
| Public DNS propagation probe | https://boce.aliyun.com/detect/dns | T-F66F330B |
| Wanxiaozhi site builder | https://dc.console.aliyun.com/next/index#/xiaozhi | T-AFD53C57 |
| Purchasable regions / instance types for this account | https://ecs-buy.aliyun.com/instanceTypes/#/instanceTypeByRegion | T-8D8F2AD9 |

## Official help docs by symptom

| Symptom | Doc | Ticket source |
|---|---|---|
| Disk attached but not visible in the OS | https://help.aliyun.com/zh/ecs/user-guide/attach-a-data-disk and https://help.aliyun.com/zh/ecs/user-guide/initialize-a-data-disk-whose-size-does-not-exceed-2-tib-on-a-linux-instance | T-37463A4B, T-69E628E3 |
| Snapshots: what they are / creating one / deleting one | https://help.aliyun.com/zh/ecs/user-guide/snapshot-overview/ ; https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot ; https://help.aliyun.com/document_detail/128131.html | T-69E628E3, T-37463A4B, T-A250313A |
| Snapshot billing (why fees exist for what I cannot see) | https://help.aliyun.com/zh/ecs/product-overview/snapshots-1 | T-69E628E3, T-D52AE555, T-67C8E3F5 |
| Restore data from a snapshot to a new disk | https://help.aliyun.com/zh/ecs/user-guide/create-a-disk-from-a-snapshot | T-69E628E3 |
| Detach a data disk / convert its billing method first | https://help.aliyun.com/zh/ecs/user-guide/detach-a-data-disk ; https://help.aliyun.com/zh/ecs/switch-the-billing-method-of-a-disk | T-5E9C11A3 |
| Re-initialize a system disk | https://help.aliyun.com/zh/ecs/user-guide/re-initialize-a-system-disk | T-69E628E3 |
| Release an instance (the product name for "shutdown forever") | https://help.aliyun.com/zh/ecs/user-guide/release-an-instance | T-804A0640, T-5E9C11A3 |
| Reset the instance login password | https://help.aliyun.com/zh/ecs/user-guide/reset-the-logon-password-of-an-instance | T-F66F330B |
| Bill settlement behavior after overdue | https://help.aliyun.com/zh/user-center/product-overview/updates-on-the-bill-settlement-policy | T-D52AE555 |
| Buying ECS / regions and zones / getting started | https://help.aliyun.com/document_detail/2361102.html ; https://help.aliyun.com/document_detail/188196.html ; https://help.aliyun.com/document_detail/2983142.html | T-8D8F2AD9 |
| IPv6 enablement and bandwidth billing | https://help.aliyun.com/zh/ecs/user-guide/step-1-create-a-vpc-that-supports-ipv6-addressing ; https://help.aliyun.com/zh/ipv6-gateway/product-overview/billing-rules | T-8B7240F7 |
| EIP application and management | https://help.aliyun.com/zh/eip/apply-for-new-eips ; https://help.aliyun.com/zh/eip/elastic-ip-address | T-AB34E2B9 |
| DNS record modification | https://help.aliyun.com/zh/dns/modify-a-dns-record ; https://help.aliyun.com/zh/dns/pubz-manage-resolution-records | T-F66F330B |
| Wanxiaozhi domain binding | https://help.aliyun.com/document_detail/2928165.html | T-AFD53C57 |
| ICP filing application | https://help.aliyun.com/zh/icp-filing/basic-icp-service/user-guide/icp-filing-application-overview | T-A250313A |
| Unsubscription rules / refund destinations | https://help.aliyun.com/zh/user-center/cancel-subscription/ ; https://help.aliyun.com/zh/user-center/user-guide/refund-destinations ; https://help.aliyun.com/document_detail/116043.html | T-B2672FDF |
| DAS billing details (a non-ECS bill line) | https://help.aliyun.com/zh/das/product-overview/billing-details | T-D91ACD63 |
| Console file upload/download on the instance detail page | https://help.aliyun.com/zh/ecs/user-guide/upload-and-download-files-on-the-instance-details-page | help-search hit; offer as the answer to "where is the FTP entry" |
| Sending a remote command from the console (customer-side use) | https://help.aliyun.com/zh/ecs/user-guide/send-remote-commands | help-search hit; this skill only navigates to it, never executes |
| Batch operations on the instance list | https://help.aliyun.com/zh/ecs/user-guide/batch-operation-of-ecs-instances-through-the-ecs-console | help-search hit |

## Terminal-form caveat

All paths above are PC web console paths. The phone app exposes a reduced
subset (T-8BBBBAF4, T-75C85AC2): when the customer reports a missing entry
from a phone, first say the app may not carry the feature and re-check in a
PC browser before treating it as a permissions or existence problem.
