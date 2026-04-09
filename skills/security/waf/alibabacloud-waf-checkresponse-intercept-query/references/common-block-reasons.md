# Common WAF Block Reasons and Recommendations

## Block Reason Reference Table

| Rule Type | Common Causes | Recommendations |
|-----------|---------------|-----------------|
| Custom Access Control (ACL) | URL/parameters matched blacklist rules | Check if request URL and parameters match business expectations |
| CC Protection | Request frequency exceeded threshold | Reduce request frequency, or request CC threshold adjustment |
| IP Blacklist/Whitelist | Client IP is on the blacklist | Verify if IP was blocked by mistake, contact admin to remove |
| Region Blocking | Source region is restricted | Verify if the access region is compliant |
| Bot Management | Identified as malicious crawler | Verify if it is a legitimate crawler, request whitelist addition |
| Data Risk Control | Triggered risk control policy | Check if request behavior is normal |

## Protection Object Naming Conventions

Protection objects are named differently based on the access method:

| Access Method | Protection Object Name Example | Description |
|---------------|-------------------------------|-------------|
| **CNAME Access** | `hhd.aliyundemo.com-waf` | Domain name + `-waf` suffix |
| **ALB Cloud Product Access** | `alb-ofywk004eo08ou0hqe-alb` | ALB instance ID + `-alb` suffix |
| **MSE Route-Level Access** | `testzhukuoroute-gw-f3d2135cd0674b2199fab5a4186596e2-mse` | Route name + `-mse` suffix |
| **ECS Instance Port-Level Access** | `i-2ze9eanh176rq8p1o0l7-80-ecs` | ECS instance ID + port + `-ecs` suffix |
| **Domain + ALB Instance-Level Access** | `abc.test.com-alb-4zej9hs2bz41kq2g52-alb` | Domain name + ALB instance ID + `-alb` suffix |
