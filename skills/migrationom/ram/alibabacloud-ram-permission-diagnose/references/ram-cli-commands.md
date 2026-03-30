# RAM-Related aliyun CLI Command Reference

> All commands are executed via the `aliyun` CLI. Credentials must be configured in advance (`aliyun configure`).

## Diagnostic Commands

### Decode Encrypted Diagnostic Message

Transcribe `EncodedDiagnosticMessage` from the error output and call directly:

```bash
aliyun ram DecodeDiagnosticMessage --EncodedDiagnosticMessage "<transcribed-value>"
```

If `EntityNotExist` is returned (transcription error), re-run the original failing command to a temp file and extract the token:

```bash
aliyun <product> <operation> [params] > /tmp/<context>.txt 2>&1
aliyun ram DecodeDiagnosticMessage \
  --EncodedDiagnosticMessage "$(grep -o 'EncodedDiagnosticMessage:[^ ]*' /tmp/<context>.txt | cut -d: -f2)"
```

### Query Current Identity
```bash
aliyun ram GetUser
```

### Resolve User Identity (UserId → UserName)

When `DecodeDiagnosticMessage` returns `AuthPrincipalType = SubUser`, the `AuthPrincipalDisplayName` is a numeric UserId that cannot be used directly in RAM APIs. Use the following command to resolve the UserName:

```bash
aliyun ims GetUser --UserId <UserId>
# Use User.UserName from the response for subsequent RAM operations
```

### List Policies Attached to a User
```bash
aliyun ram ListPoliciesForUser --UserName <username>
```

### List Policies Attached to a Role
```bash
aliyun ram ListPoliciesForRole --RoleName <rolename>
```

### Read Policy Content (get current version document)
```bash
# First get the policy default version
aliyun ram GetPolicy --PolicyName <policy-name> --PolicyType Custom

# Read the policy document for a specific version
aliyun ram GetPolicyVersion \
  --PolicyName <policy-name> \
  --PolicyType Custom \
  --VersionId <version-id>
```

### List Policy Versions
```bash
aliyun ram ListPolicyVersions \
  --PolicyName <policy-name> \
  --PolicyType Custom
```

---

## System Policy Repair Commands

### Attach System Policy to a RAM User
```bash
aliyun ram AttachPolicyToUser \
  --PolicyName <system-policy-name> \
  --PolicyType System \
  --UserName <username>
```

### Attach System Policy to a RAM Role
```bash
aliyun ram AttachPolicyToRole \
  --PolicyName <system-policy-name> \
  --PolicyType System \
  --RoleName <rolename>
```

### Detach System Policy
```bash
# Detach from user
aliyun ram DetachPolicyFromUser \
  --PolicyName <system-policy-name> \
  --PolicyType System \
  --UserName <username>

# Detach from role
aliyun ram DetachPolicyFromRole \
  --PolicyName <system-policy-name> \
  --PolicyType System \
  --RoleName <rolename>
```

---

## Custom Policy Repair Commands

### Create Custom Policy (first time)
```bash
aliyun ram CreatePolicy \
  --PolicyName <policy-name> \
  --PolicyDocument '{"Version":"1","Statement":[{"Effect":"Allow","Action":["svc:Action"],"Resource":"acs:svc:*:*:*"}]}'
```

### Attach Custom Policy to a User
```bash
aliyun ram AttachPolicyToUser \
  --PolicyName <policy-name> \
  --PolicyType Custom \
  --UserName <username>
```

### Attach Custom Policy to a Role
```bash
aliyun ram AttachPolicyToRole \
  --PolicyName <policy-name> \
  --PolicyType Custom \
  --RoleName <rolename>
```

### Append New Actions (update policy version)
```bash
# Step 1: Get current policy content (check version first)
aliyun ram GetPolicy --PolicyName <policy-name> --PolicyType Custom
# Note the DefaultVersion field value, e.g., v3

# Step 2: Read the current version document
aliyun ram GetPolicyVersion \
  --PolicyName <policy-name> \
  --PolicyType Custom \
  --VersionId v3

# Step 3 (if 5 versions already exist): delete the oldest non-default version
aliyun ram DeletePolicyVersion \
  --PolicyName <policy-name> \
  --PolicyType Custom \
  --VersionId v1

# Step 4: Create new version (complete JSON with existing + new Actions)
aliyun ram CreatePolicyVersion \
  --PolicyName <policy-name> \
  --PolicyType Custom \
  --PolicyDocument '{"Version":"1","Statement":[...all Actions...]}' \
  --SetAsDefault true
```

### Detach Custom Policy
```bash
# Detach from user
aliyun ram DetachPolicyFromUser \
  --PolicyName <policy-name> \
  --PolicyType Custom \
  --UserName <username>

# Detach from role
aliyun ram DetachPolicyFromRole \
  --PolicyName <policy-name> \
  --PolicyType Custom \
  --RoleName <rolename>
```

### Delete Custom Policy (all versions + the policy itself)
```bash
# First delete all non-default versions
aliyun ram DeletePolicyVersion --PolicyName <policy-name> --PolicyType Custom --VersionId v1
# ...repeat until only the default version remains

# Then delete the policy (automatically removes the last version)
aliyun ram DeletePolicy --PolicyName <policy-name> --PolicyType Custom
```

---

## Role Trust Policy Repair Commands

Use this sequence when root cause is "trust policy not allowing caller":

```bash
# Step 1: Get current trust policy content
aliyun ram GetRole --RoleName <role-name>
# Note the AssumeRolePolicyDocument field

# Step 2: Update trust policy (add caller ARN to Principal.RAM array)
aliyun ram UpdateRole \
  --RoleName <role-name> \
  --NewAssumeRolePolicyDocument '{"Statement":[{"Action":"sts:AssumeRole","Effect":"Allow","Principal":{"RAM":["acs:ram::<account-id>:root","acs:ram::<account-id>:user/<caller-username>"]}}],"Version":"1"}'

# Undo: restore original Principal by calling UpdateRole again with original JSON
aliyun ram UpdateRole \
  --RoleName <role-name> \
  --NewAssumeRolePolicyDocument '<original-json>'
```

If caller identity policy also lacks `sts:AssumeRole`, attach the system policy:
```bash
aliyun ram AttachPolicyToUser \
  --PolicyName AliyunSTSAssumeRoleAccess \
  --PolicyType System \
  --UserName <username>

# Undo
aliyun ram DetachPolicyFromUser \
  --PolicyName AliyunSTSAssumeRoleAccess \
  --PolicyType System \
  --UserName <username>
```

If role name is unknown, list roles first:
```bash
aliyun ram ListRoles
```

---

## Service-Linked Role Commands

```bash
# Create a service-linked role
aliyun ram CreateServiceLinkedRole \
  --ServiceName <service>.aliyuncs.com

# Check whether a service-linked role exists
aliyun ram GetRole --RoleName AliyunServiceRole<ServiceName>
```

---

## CP Control Policy Query Commands (ResourceDirectory)

```bash
# List all control policies
aliyun ram ListControlPolicies

# View a specific control policy's content
aliyun ram GetControlPolicy --PolicyId <policy-id>
```
