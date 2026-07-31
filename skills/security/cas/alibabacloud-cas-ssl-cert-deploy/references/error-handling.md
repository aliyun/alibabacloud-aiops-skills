# Error Handling — SSL Certificate Deployment

Consolidated error codes and resolutions for all deployment operations.

## Core Deployment Errors

| Error Scenario | Resolution |
|---------------|-----------|
| `$CERT_PROFILE` not set | Prompt to run `alibabacloud-cas-ssl-common-tools` Identity Resolver first |
| No `CertId` | Ask user, or read from `$CERT_CERT_ID` |
| `InvalidCertId.NotFound` | Certificate doesn't exist, verify CertId |
| `ListCloudResources` no domain match | Guide user to create the matching domain resource first |
| `InvalidParameter` | Check format: `--cert-ids`/`--resource-ids`/`--contact-ids` comma-separated, `--job-type` lowercase |
| `InvalidResourceId.NotFound` | Resource does not exist, verify ResourceId |
| `ResourceNotSupportCert` | Resource does not support cert deployment, verify cloud product instance exists |
| `Forbidden.RAM` | Insufficient permissions, verify RAM user has required CAS/CDN/ALB/WAF actions |
| Deployment job `FailedCount > 0` | Use `list-worker-resource --status error`, report failure details to user |
| curl verification failed | Check domain resolution, cloud product binding, wait for config |

## CAS Deployment Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `InvalidCertId.NotFound` | Certificate does not exist | Verify CertId is correct |
| `InvalidResourceId.NotFound` | Resource does not exist | Verify ResourceId is correct |
| `ResourceNotSupportCert` | Resource does not support cert deployment | Verify the cloud product instance exists |
| `DeploymentJobFailed` | Deployment job failed | Check `describe-deployment-job` error details |
| `Forbidden.RAM` | Insufficient permissions | Verify RAM policy includes cloud product deployment permissions |

## ALB Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ResourceNotFound.LoadBalancer` | ALB instance does not exist | Verify ALB ID and region |
| `ResourceNotFound.Listener` | Listener does not exist | Verify listener ID with `list-listeners` |
| `ListenerAlreadyExists` | Duplicate protocol+port | Use `update-listener-attribute` instead |
| `ResourceNotFound.ServerGroup` | Server group does not exist | Verify server group ID and VPC |
| `IncorrectListenerStatus` | Listener not in `Running` state | Wait for listener status to become `Running` |

## CDN Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `RetErrorSourceCircle` | Origin is already a CDN domain | Change origin server |
| `DomainOwnerVerifyFail` | Domain ownership not verified | Add DNS TXT record |
| `DomainOverLimit` | Domain limit reached (default 50) | Submit ticket |
| `RecordCheckNotAvailable` | Domain not ICP-filed + mainland region | Complete ICP or switch to `overseas` |

## WAF Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Waf.Pullin.ResourceExsit` | Domain already onboarded | Proceed to deployment |
| `RegionId` error | Invalid region | Use `cn-hangzhou` or `ap-southeast-1` |

## OSS Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `NeedVerifyDomainOwnership` | Domain not verified | Execute CreateCnameToken step |
| `CnameAlreadyExists` | Domain bound to another Bucket | Unbind first |
| `NoSuchCnameInRecord` | Domain not ICP-registered | Complete ICP filing |

