# Common Migration Errors and Remediation

This document provides a structured reference for common failures encountered during AWS → Alibaba Cloud migration, organized by migration tool and phase. Each error includes the root cause and actionable remediation steps.

---

## 1. Terraform (IaCService) Errors

| Error Pattern | Cause | Remediation |
|---|---|---|
| `Error: creating VPC: Forbidden.RAM` | Missing RAM permissions for VPC operations | Attach `AliyunVPCFullAccess` policy to the RAM user. See `ram-policies.md` for complete policy list |
| `Error: InvalidCidrBlock` | CIDR block format invalid or conflicts with existing VPC | Check CIDR format (e.g., `10.0.0.0/8`). Ensure no overlap with existing VPCs using `aliyun vpc DescribeVpcs --user-agent AlibabaCloud-Agent-Skills` |
| `Error: QuotaExceeded.xxx` | Resource quota limit reached for the account/region | Request quota increase via Alibaba Cloud Console → Quota Center. Check current quota: `aliyun ecs DescribeAccountAttributes --user-agent AlibabaCloud-Agent-Skills` |
| `Error: IdempotentParameterMismatch` | Same resource name used with different parameters in subsequent apply | Use unique resource names per environment, or import existing resource with `terraform import <resource_type>.<name> <resource_id>` |
| `Error: OperationDenied.xxx` | Resource in wrong state for the requested operation | Wait for resource to reach target state, then retry. Check resource status in console or via CLI: `aliyun <service> Describe<Resources> --user-agent AlibabaCloud-Agent-Skills` |
| `Error: InvalidZone.NotOnSale` | Instance type not available in chosen zone | Change ZoneId or InstanceType. Check availability: `aliyun ecs DescribeAvailableResource --RegionId <region> --InstanceType <type> --user-agent AlibabaCloud-Agent-Skills` |
| State lock error / STATE_ID conflict | Concurrent operations on same Terraform state file | Wait for previous IaCService task to complete. Check IaCService task status. If stuck, contact admin to release lock |
| `Error: timeout while waiting for state` | Resource creation/update timed out waiting for target state | Check resource status in console. If created successfully, import into state. If not, check event logs and retry |
| `Error: Provider produced inconsistent result` | Provider returned different resource attributes than expected | Run `terraform refresh` to sync state. If persists, check provider version compatibility in `terraform-providers/alicloud.md` |
| `Error: InvalidAccessKeyId.NotFound` | AccessKey ID does not exist or is inactive | Verify AccessKey is active in RAM console. Ensure correct AK/SK configured in IaCService task |

---

## 2. SMC (Server Migration) Errors

| Error Pattern | Cause | Remediation |
|---|---|---|
| Migration stuck at progress < 100% for extended period | Large disk size, slow network bandwidth, or SMC agent issue | Check SMC agent logs on source server (`/root/go2aliyun_client.log`). Consider increasing bandwidth or using VPC-based migration (NetMode=2) for better throughput |
| `SourceServerNotFound` | SMC agent not registered with Alibaba Cloud SMC service | Install and start SMC agent on source EC2. Verify agent connectivity to Alibaba Cloud endpoint: `telnet smc.<region>.aliyuncs.com 8080` |
| `Forbidden.InstanceExist` | Intermediate migration instance already exists from previous job | Delete existing intermediate instance via ECS console, or use a different migration job name |
| Image creation failed | Disk size exceeds limits or unsupported filesystem type | Check source disk size (<500GB recommended for single migration). Verify filesystem type is supported (ext3/ext4/xfs/ntfs). For larger disks, use incremental migration |
| `IntranetIpConflict` | Target IP conflicts with existing IP in VSwitch | Adjust VSwitch CIDR or specify a different VSwitch for the migration job. Check available IPs: `aliyun vpc DescribeVSwitches --VSwitchId <id> --user-agent AlibabaCloud-Agent-Skills` |
| Agent disconnected during migration | Network interruption between source and Alibaba Cloud | Restart SMC agent on source server. Migration supports resumption — it will continue from last checkpoint automatically |
| `InvalidAccountStatus.NotEnoughBalance` | Insufficient account balance for pay-as-you-go resources | Top up Alibaba Cloud account. SMC creates intermediate pay-as-you-go instances during migration |
| `InvalidParameter.Encrypted` | Source disk is encrypted and key not available | Export encrypted AMI with shared KMS key, or create unencrypted copy first. Alibaba Cloud does not support direct encrypted AMI import |
| `ReplicationJobNotReady` | Replication job not in correct state for operation | Wait for job to reach `Ready` state. Check status: `aliyun smc DescribeReplicationJobs --ReplicationJobId <id> --user-agent AlibabaCloud-Agent-Skills` |
| `Go2AliyunClientError` | SMC agent encountered internal error | Check agent logs at `/root/go2aliyun_client.log`. Common fixes: restart agent, verify network connectivity, ensure sufficient disk space |

---

## 3. DTS (Database Migration) Errors

| Error Pattern | Cause | Remediation |
|---|---|---|
| Pre-check failed: connectivity | Source RDS not accessible from DTS service | Configure AWS RDS security group to allow DTS IP ranges (check DTS console for IPs). Or use public endpoint with SSL enabled |
| Pre-check failed: privileges | Database user lacks required replication permissions | Grant REPLICATION SLAVE, REPLICATION CLIENT privileges on source MySQL. For PostgreSQL: grant SUPERUSER or specific replication role |
| Pre-check failed: binlog | Binary logging not enabled on source RDS | Enable binary logging on source RDS: set `binlog_format=ROW`, `binlog_row_image=FULL`, `expire_logs_days>=7`. Requires RDS parameter group modification |
| Sync lag increasing continuously | High write volume on source exceeding DTS throughput | Increase DTS instance specification (Small→Medium→Large). Consider scheduling migration during low-traffic window |
| Schema migration failed: DDL syntax error | Source DDL uses syntax incompatible with target | Manually create the table on target with compatible syntax, then configure DTS to skip schema migration for that table |
| `OperationDenied.JobStatus` | DTS job in wrong state for requested operation | Check job status in console. May need to stop running job before reconfiguration. Some operations only allowed in `NotStarted` state |
| Character set mismatch | Source uses charset not supported by target RDS | Verify charset compatibility before migration. Use `utf8mb4` for broad compatibility. Check target supported charsets in RDS console |
| `DtsJobIdNotExist` | DTS job ID does not exist or was deleted | Verify job ID in DTS console. Job may have been deleted or never created. Re-create migration job if needed |
| `TargetDbNotReady` | Target RDS instance not in running state | Start target RDS instance. Ensure instance is accessible and in `Running` state before starting DTS job |
| Data consistency check failed | Source and target data mismatch after full migration | Run DTS data consistency check. For mismatches, use DTS repair function or manually reconcile affected tables |

---

## 4. Storage Migration (OSS) Errors

| Error Pattern | Cause | Remediation |
|---|---|---|
| `AccessDenied` on source S3 | AWS IAM user lacks required S3 permissions | Ensure AWS IAM user has `s3:GetObject`, `s3:ListBucket`, `s3:GetBucketLocation` on source bucket. Add bucket policy if cross-account |
| `BucketAlreadyExists` | OSS bucket name already taken globally | Choose a different bucket name (OSS bucket names are globally unique across all Alibaba Cloud accounts). Use naming convention: `<company>-<region>-<purpose>` |
| Transfer speed too slow | Single-threaded transfer or suboptimal part size | Use `--part-size` and `--parallel` flags with ossutil (e.g., `ossutil cp -r --parallel 10 --part-size 100M`). Or use Data Online Migration for server-side transfer |
| Large file upload timeout | File exceeds single upload timeout threshold | Use multipart upload (automatic with ossutil for files >100MB). Increase timeout: `ossutil config --timeout 3600` |
| Object count mismatch after migration | Hidden objects, versioned objects, or delete markers not migrated | Enable versioning on source listing. Check for delete markers. Re-run with `--include-all-versions` flag or use Data Online Migration |
| `InvalidObjectState` | Source object in Glacier/cold storage tier | Restore object from Glacier before migration. ossutil cannot directly migrate objects in cold storage |
| `NoSuchBucket` | Source S3 bucket does not exist or name typo | Verify bucket name and region. Check bucket exists: `aws s3 ls s3://<bucket-name> --region <region>` |
| MD5 checksum mismatch | Object corrupted during transfer | Re-transfer affected objects. Use `ossutil cp --checksum` to verify integrity. Check network stability |
| `RequestTimeTooSkewed` | Source server clock significantly out of sync | Synchronize source server clock with NTP. Alibaba Cloud requires clock skew < 15 minutes |

---

## 5. Function Compute (FC) Errors

| Error Pattern | Cause | Remediation |
|---|---|---|
| `InvalidArgument.handler` | Handler format doesn't match FC convention | FC handler format: `index.handler` (file.function). Adjust from Lambda format if different. Check `terraform-providers/alicloud.md` for FC resource specs |
| `ServiceNotFound` / `FunctionNotFound` | Wrong service or function name in invocation | Verify service and function names match Terraform resource names. List functions: `aliyun fc list-functions --service-name <service> --user-agent AlibabaCloud-Agent-Skills` |
| Timeout during invocation | Function execution timeout too low for workload | Increase `timeout` in Terraform config (FC max: 600s for on-demand, 86400s for async tasks). Consider async invocation for long-running tasks |
| `FunctionNotFound` after terraform apply | Using deprecated resource type | Use `alicloud_fcv3_function` (not deprecated `alicloud_fc_function`). Check `terraform-providers/alicloud.md` for current resource types |
| Permission denied accessing OSS/RDS from FC | Missing RAM role or service-linked role | Create service-linked role for FC with access to required resources. Attach `AliyunFCDefaultRole` or custom policy with specific resource permissions |
| `InvalidArgument.Runtime` | Runtime version not supported by FC | Check supported runtimes in FC console. Common: `python3.9`, `nodejs18`, `java11`, `custom-container`. Update Terraform config accordingly |
| `CodeSizeExceeded` | Deployment package exceeds size limit | FC code size limit: 50MB (zip), 500MB (layer). Use layers for dependencies, or store large assets in OSS and download at runtime |
| `ConcurrentInvocationExceeded` | Function concurrent execution limit reached | Request quota increase for concurrent invocations. Implement request queuing or increase provisioned concurrency |
| `ServiceQuotaExceeded` | Account exceeded FC resource quotas | Check quotas in FC console. Request increase for: functions per service, memory per function, or total storage |

---

## 6. DNS & CDN Errors

| Error Pattern | Cause | Remediation |
|---|---|---|
| `DomainNotFound` | Domain not added to Alibaba Cloud DNS | Add domain first via `alicloud_dns_domain` resource or DNS console. Verify domain ownership if required |
| DNS propagation delay causing downtime | TTL not expired before cutover | Lower TTL to 60s at least 24-48 hours before migration. Wait for old TTL to expire, then migrate. Raise TTL after verification |
| CDN `OriginNotAccessible` | Origin server not reachable from Alibaba Cloud CDN nodes | Check origin server firewall/security group allows Alibaba Cloud CDN IP ranges. Add health check endpoint |
| Certificate error on CDN domain | SSL certificate not uploaded or associated with CDN domain | Upload certificate to Certificate Management Service, then associate with CDN domain. Ensure cert matches domain exactly |
| `DomainAlreadyExists` | Domain already configured in another Alibaba Cloud account | Domain must be transferred or removed from other account. Contact Alibaba Cloud support if account access unavailable |
| `RecordConflict` | DNS record conflicts with existing record | Delete or modify conflicting record. CNAME cannot coexist with other records at same name |
| CDN cache not refreshing after origin update | Cache TTL not expired or purge not triggered | Manually purge CDN cache via console or API: `aliyun cdn RefreshObjectCaches --ObjectPath <url> --user-agent AlibabaCloud-Agent-Skills` |
| `Forbidden.Domain` | Domain blocked or requires ICP filing | For China regions, ensure domain has valid ICP filing. Check domain status in ICP management console |

---

## Quick Reference: Error → Phase Mapping

| If you see... | Check phase... |
|---|---|
| `RAM`, `Forbidden`, `Access Denied`, `Unauthorized` | All phases — RAM permission issue |
| `SMC`, `ReplicationJob`, `SourceServer`, `Go2Aliyun` | Phase 3: Server Migration |
| `DTS`, `MigrationJob`, `binlog`, `sync`, `precheck` | Phase 4: Database Migration |
| `OSS`, `Bucket`, `Object`, `ossutil` | Phase 5: Storage Migration |
| `FC`, `Function`, `Service`, `handler`, `runtime` | Phase 6: Serverless Migration |
| `DNS`, `Domain`, `CDN`, `CNAME`, `TTL` | Phase 7: DNS & CDN |
| `Terraform`, `STATE_ID`, `HCL`, `Provider` | All phases — Terraform/IaCService issue |
| `QuotaExceeded`, `LimitExceeded` | All phases — Resource quota issue |
| `InvalidParameter`, `InvalidArgument` | All phases — Configuration error |
| `Timeout`, `ConnectionRefused`, `NetworkUnreachable` | All phases — Network/connectivity issue |

---

## General Troubleshooting Principles

### 1. Check Logs First
- **Terraform**: Review IaCService task logs in console
- **SMC**: Check `/root/go2aliyun_client.log` on source server
- **DTS**: View task logs in DTS console → Task Details → Logs
- **OSS**: Use `ossutil ls oss://bucket --all-versions` for detailed listing
- **FC**: Check function logs in Log Service (SLS) linked to FC

### 2. Verify Permissions
Most `Forbidden` or `AccessDenied` errors stem from RAM policy gaps. Reference `ram-policies.md` for required policies per service.

### 3. Check Resource State
Before retrying operations, verify current resource state:
```bash
# ECS instance status
aliyun ecs DescribeInstances \
  --InstanceIds '["i-xxx"]' \
  --user-agent AlibabaCloud-Agent-Skills

# DTS job status
aliyun dts DescribeMigrationJobs \
  --MigrationJobId <id> \
  --user-agent AlibabaCloud-Agent-Skills

# SMC job status
aliyun smc DescribeReplicationJobs \
  --ReplicationJobId <id> \
  --user-agent AlibabaCloud-Agent-Skills
```

### 4. Use Dry-Run When Available
- Terraform: `terraform plan` before `apply`
- DTS: Run pre-check before starting migration
- SMC: Validate migration job before execution

### 5. Contact Support When
- Error persists after following remediation steps
- Quota increase required
- Cross-account or cross-region complexity
- Data consistency issues after migration

---

## Related Documents

- `verification-method.md` — Success verification commands and expected outputs
- `ram-policies.md` — Required RAM policies for migration operations
- `terraform-providers/alicloud.md` — Terraform provider reference
- `terraform-online-runtime.md` — IaCService Terraform execution guide
