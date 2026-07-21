# Error Handling — SSL Certificate Purchase

Complete error handling reference for the alibabacloud-cas-ssl-cert-purchase skill.

## Error Handling Table

| Error Scenario | Resolution |
|---------------|-----------|
| `$CERT_PROFILE` not set | Use fallback: `aliyun configure list` to identify active profile |
| `DomainAndProductNotMatch` | TEST instance domain restriction. Offer: 1) New TEST in console; 2) Switch to BUY DV |
| No inactive instances | Auto-purchase via BSS (see Instance Purchase section) |
| `CompanyId` missing (OV/EV) | Guide to Console → Information Management |
| `ContactIdList` missing | Guide to Console → Information Management → Contacts |
| `Forbidden` | Check credential permissions, follow Permission Failure Handling in SKILL.md |
| apply-certificate task failed | Show error details from `get-task-attribute` |
| BSS `COMMODITY.INVALID_COMPONENT` | The spec code is invalid for the chosen CA/type/duration on this site. Spec format: `{brand_prefix}.{type}.{domain_mode}` (e.g. `ali.dv.f`, `ss.dv.w`); brand prefixes: `ali`=Alibaba, `ss`=DigiCert, `gs`=GlobalSign, `geo`=GeoTrust, `vt`=vTrus, `cf`=CFCA, `sh`=WoTrus, `ws`=WoSign, `rap`=Rapid, `ssp`=DigiCert Pro. Re-confirm CA, type and duration with the user, then retry with a valid combination |
| BSS `INSUFFICIENT.AVAILABLE.QUOTA` | 1. Show error to user; 2. Direct to top up: https://usercenter2.aliyun.com/ ; 3. Wait for the user to confirm top-up; 4. Retry purchase (user-driven only) |
| BSS `ProductCode.NotFound` (intl) | Confirm account is international site |
| BSS `create-instance` timeout | **Do NOT auto-retry** — a timeout does not mean the order failed, and retrying may double-charge. First query `get-order-detail` to check whether an order was already created. Only retry if confirmed none exists; otherwise fall back to console purchase |
| Network error mid-workflow | Re-check instance status via `get-instance-detail`. If instance was purchased but not yet updated, resume from Step 4. If update done but apply not submitted, resume from Step 5 |
| Task polling timeout (20 attempts) | Inform user application is still processing. Provide task ID and `get-instance-detail` command for manual checking. For OV/EV, explain 1-5 business day review period |
| OV/EV application rejected | Check `get-instance-detail` for rejection reason. Guide user to correct company/contact info and resubmit. If rejected twice, suggest console application |
| BSS plugin unavailable (intl) | If `check-plugin` fails: 1. Install: `aliyun plugin install --names aliyun-cli-bssopenapi`; 2. If install fails, purchase via console: https://yundun.console.alibabacloud.com/?p=cas |
| `list-instances` returns empty | Distinguish: empty `Instances` array with HTTP 200 = genuinely no instances (proceed to purchase). A `Forbidden` error = permission issue (follow Permission Failure Handling) |
