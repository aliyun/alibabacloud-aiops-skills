# RAM Policies: Build AI Animation Story Creation App

**Scenario**: Build AI Animation Story Creation App (Auto Deploy)

---

## Required RAM Permissions

### 1. Devs (Serverless Development Platform)

| Action | Description | Used In |
|--------|-------------|---------|
| `devs:CreateProject` | Create project with template configuration | Step 3 |
| `devs:RenderServicesByTemplate` | Render template to get service configuration | Step 4a |
| `devs:UpdateEnvironment` | Update environment configuration (write services and roleArn) | Step 4a |
| `devs:DeployEnvironment` | Trigger environment deployment | Step 4b |
| `devs:ListEnvironments` | List project environments | Step 5 |
| `devs:GetEnvironment` | Query environment details and deployment status | Step 5 |

### 2. FC (Function Compute 3.0)

> Devs template deployment internally requires FC permissions to create functions and triggers. Custom domain creation also requires FC permissions.

| Action | Description | Used In |
|--------|-------------|---------|
| `fc:CreateFunction` | Create function | Devs internal call |
| `fc:GetFunction` | Query function details | Devs internal call |
| `fc:CreateTrigger` | Create trigger | Devs internal call |
| `fc:CreateCustomDomain` | Create custom domain | Step 6 |
| `fc:DeleteCustomDomain` | Delete custom domain (cleanup) | Resource cleanup |

System policy: `AliyunFCFullAccess`

### 3. OSS (Object Storage Service)

| Action | Description | Used In |
|--------|-------------|---------|
| `oss:PutBucket` | Create Bucket | Step 2 |
| `oss:GetBucketInfo` | Query Bucket info | Step 2 verification |
| `oss-admin:OpenOssService` | Enable OSS service | Step 2 |

System policy: `AliyunOSSFullAccess`

### 4. STS

| Action | Description | Used In |
|--------|-------------|---------|
| `sts:GetCallerIdentity` | Get current user UID (to construct roleArn) | Step 4 |

### 5. RAM

| Action | Description | Used In |
|--------|-------------|---------|
| `ram:GetRole` | Query role trust policy | Step 4 |
| `ram:CreateRole` | Create role (auto-create if role does not exist) | Step 4 |
| `ram:UpdateRole` | Update role trust policy (add FC service trust) | Step 4 |
| `ram:AttachPolicyToUser` | Attach system policy to RAM user | RAM Policy pre-check |

### 6. DashScope / MaaS (Bailian)

> Bailian API Key is automatically created and managed via the `aliyun maas` CLI plugin.

| Action | Description | Used In |
|--------|-------------|---------|
| `maas:ListWorkspaces` | Get workspace list | Step 1 |
| `maas:CreateWorkspace` | Create workspace (auto-create if none exists) | Step 1 |
| `maas:CreateApiKey` | Create API Key | Step 1 |
| `maas:DeleteApiKey` | Delete API Key (cleanup) | Resource cleanup |

---

## Recommended System Policies

| Policy | Description |
|--------|-------------|
| `AliyunFCFullAccess` | Full access to Function Compute |
| `AliyunOSSFullAccess` | Full access to OSS |
