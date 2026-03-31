# Migration Status Tracker

## Status Legend
| Emoji | Status | Description |
|-------|--------|-------------|
| ⬜ | Not Started | Resource identified but migration not begun |
| 🔄 | In Progress | Migration actively running |
| ⏸️ | Paused | Migration paused (awaiting user action or dependency) |
| ✅ | Completed | Migration finished and verified |
| ❌ | Failed | Migration failed — see error details |
| 🔙 | Rolled Back | Resource rolled back to source |

## Overall Progress
```
Phase 1: Assessment     [✅ / ⬜]
Phase 2: Network        [✅ / ⬜]
Phase 3: Servers        [✅ / ⬜]
Phase 4: Databases      [✅ / ⬜]
Phase 5: Storage        [✅ / ⬜]
Phase 6: Serverless     [✅ / ⬜]
Phase 7: DNS & CDN      [✅ / ⬜]
```

## Resource Migration Status
| # | Resource Name | AWS Service | Alibaba Cloud Target | Migration Tool | Phase | Status | STATE_ID | Error Details | Last Updated |
|---|---------------|-------------|---------------------|----------------|-------|--------|----------|---------------|-------------|
| 1 | `example-vpc` | VPC | VPC | Terraform | 2 | ⬜ | — | — | YYYY-MM-DD |
| 2 | `web-server-1` | EC2 | ECS | SMC + Terraform | 3 | ⬜ | — | — | YYYY-MM-DD |
| 3 | `main-db` | RDS MySQL | ApsaraDB RDS | DTS + Terraform | 4 | ⬜ | — | — | YYYY-MM-DD |
| 4 | `data-bucket` | S3 | OSS | Data Online Migration | 5 | ⬜ | — | — | YYYY-MM-DD |
| 5 | `api-handler` | Lambda | Function Compute | Terraform | 6 | ⬜ | — | — | YYYY-MM-DD |
| 6 | `example.com` | Route53 | Alibaba Cloud DNS | Terraform | 7 | ⬜ | — | — | YYYY-MM-DD |

## Usage Instructions
- Create this file as `migration-status.md` in the working directory at the start of Phase 1
- Update the status emoji after each operation (migration start, completion, failure)
- Record STATE_ID from Terraform applies for traceability
- Record error details for any ❌ status
- Update `Last Updated` timestamp on every change

## Verification Checklist

#### Phase 1: Assessment Verification
- [ ] All resources in this phase show ✅
- [ ] Terraform state IDs recorded
- [ ] Verification commands passed (see verification-method.md)
- [ ] User confirmed ready to proceed to next phase

#### Phase 2: Network Verification
- [ ] All resources in this phase show ✅
- [ ] Terraform state IDs recorded
- [ ] Verification commands passed (see verification-method.md)
- [ ] User confirmed ready to proceed to next phase

#### Phase 3: Servers Verification
- [ ] All resources in this phase show ✅
- [ ] Terraform state IDs recorded
- [ ] Verification commands passed (see verification-method.md)
- [ ] User confirmed ready to proceed to next phase

#### Phase 4: Databases Verification
- [ ] All resources in this phase show ✅
- [ ] Terraform state IDs recorded
- [ ] Verification commands passed (see verification-method.md)
- [ ] User confirmed ready to proceed to next phase

#### Phase 5: Storage Verification
- [ ] All resources in this phase show ✅
- [ ] Terraform state IDs recorded
- [ ] Verification commands passed (see verification-method.md)
- [ ] User confirmed ready to proceed to next phase

#### Phase 6: Serverless Verification
- [ ] All resources in this phase show ✅
- [ ] Terraform state IDs recorded
- [ ] Verification commands passed (see verification-method.md)
- [ ] User confirmed ready to proceed to next phase

#### Phase 7: DNS & CDN Verification
- [ ] All resources in this phase show ✅
- [ ] Terraform state IDs recorded
- [ ] Verification commands passed (see verification-method.md)
- [ ] User confirmed ready to proceed to next phase
