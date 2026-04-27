# RAM-Related aliyun CLI Command Reference

> All commands are executed via the `aliyun` CLI. Credentials must be configured in advance (`aliyun configure`).

## Diagnostic Commands

### Decode Encrypted Diagnostic Message

Transcribe `EncodedDiagnosticMessage` from the error output and call directly:

```bash
aliyun ram decode-diagnostic-message --encoded-diagnostic-message "<transcribed-value>"
```

If `EntityNotExist` is returned (transcription error), re-run the original failing command to a temp file and extract the token:

```bash
aliyun <product> <operation> [params] > /tmp/<context>.txt 2>&1
aliyun ram decode-diagnostic-message \
  --encoded-diagnostic-message "$(grep -o 'EncodedDiagnosticMessage:[^ ]*' /tmp/<context>.txt | cut -d: -f2)"
```

### Query Current Identity
```bash
aliyun ram get-user
```

### Resolve User Identity (UserId → UserName)

When `DecodeDiagnosticMessage` returns `AuthPrincipalType = SubUser`, the `AuthPrincipalDisplayName` is a numeric UserId that cannot be used directly in RAM APIs. Use the following command to resolve the UserName:

```bash
aliyun ims get-user --user-id <UserId>
# Use User.UserName from the response for subsequent RAM operations
```

### List Policies Attached to a User
```bash
aliyun ram list-policies-for-user --user-name <username>
```

### List Policies Attached to a Role
```bash
aliyun ram list-policies-for-role --role-name <rolename>
```

### Read Policy Content (get current version document)
```bash
# First get the policy default version
aliyun ram get-policy --policy-name <policy-name> --policy-type Custom

# Read the policy document for a specific version
aliyun ram get-policy-version \
  --policy-name <policy-name> \
  --policy-type Custom \
  --version-id <version-id>
```

### List Policy Versions
```bash
aliyun ram list-policy-versions \
  --policy-name <policy-name> \
  --policy-type Custom
```

---

## System Policy Repair Commands

### Attach System Policy to a RAM User
```bash
aliyun ram attach-policy-to-user \
  --policy-name <system-policy-name> \
  --policy-type System \
  --user-name <username>
```

### Attach System Policy to a RAM Role
```bash
aliyun ram attach-policy-to-role \
  --policy-name <system-policy-name> \
  --policy-type System \
  --role-name <rolename>
```

### Detach System Policy
```bash
# Detach from user
aliyun ram detach-policy-from-user \
  --policy-name <system-policy-name> \
  --policy-type System \
  --user-name <username>

# Detach from role
aliyun ram detach-policy-from-role \
  --policy-name <system-policy-name> \
  --policy-type System \
  --role-name <rolename>
```

---

## Custom Policy Repair Commands

### Create Custom Policy (first time)
```bash
aliyun ram create-policy \
  --policy-name <policy-name> \
  --policy-document '{"Version":"1","Statement":[{"Effect":"Allow","Action":["svc:Action"],"Resource":"acs:svc:*:*:*"}]}'
```

### Attach Custom Policy to a User
```bash
aliyun ram attach-policy-to-user \
  --policy-name <policy-name> \
  --policy-type Custom \
  --user-name <username>
```

### Attach Custom Policy to a Role
```bash
aliyun ram attach-policy-to-role \
  --policy-name <policy-name> \
  --policy-type Custom \
  --role-name <rolename>
```

### Append New Actions (update policy version)
```bash
# Step 1: Get current policy content (check version first)
aliyun ram get-policy --policy-name <policy-name> --policy-type Custom
# Note the DefaultVersion field value, e.g., v3

# Step 2: Read the current version document
aliyun ram get-policy-version \
  --policy-name <policy-name> \
  --policy-type Custom \
  --version-id v3

# Step 3 (if 5 versions already exist): delete the oldest non-default version
aliyun ram delete-policy-version \
  --policy-name <policy-name> \
  --version-id v1

# Step 4: Create new version (complete JSON with existing + new Actions)
aliyun ram create-policy-version \
  --policy-name <policy-name> \
  --policy-document '{"Version":"1","Statement":[...all Actions...]}' \
  --set-as-default true
```

### Detach Custom Policy
```bash
# Detach from user
aliyun ram detach-policy-from-user \
  --policy-name <policy-name> \
  --policy-type Custom \
  --user-name <username>

# Detach from role
aliyun ram detach-policy-from-role \
  --policy-name <policy-name> \
  --policy-type Custom \
  --role-name <rolename>
```

### Delete Custom Policy (all versions + the policy itself)
```bash
# First delete all non-default versions
aliyun ram delete-policy-version --policy-name <policy-name> --version-id v1
# ...repeat until only the default version remains

# Then delete the policy (automatically removes the last version)
aliyun ram delete-policy --policy-name <policy-name>
```

---

## Role Trust Policy Repair Commands

Use this sequence when root cause is "trust policy not allowing caller":

```bash
# Step 1: Get current trust policy content
aliyun ram get-role --role-name <role-name>
# Note the AssumeRolePolicyDocument field

# Step 2: Update trust policy (add caller ARN to Principal.RAM array)
aliyun ram update-role \
  --role-name <role-name> \
  --new-assume-role-policy-document '{"Statement":[{"Action":"sts:AssumeRole","Effect":"Allow","Principal":{"RAM":["acs:ram::<account-id>:root","acs:ram::<account-id>:user/<caller-username>"]}}],"Version":"1"}'

# Undo: restore original Principal by calling UpdateRole again with original JSON
aliyun ram update-role \
  --role-name <role-name> \
  --new-assume-role-policy-document '<original-json>'
```

If caller identity policy also lacks `sts:AssumeRole`, attach the system policy:
```bash
aliyun ram attach-policy-to-user \
  --policy-name AliyunSTSAssumeRoleAccess \
  --policy-type System \
  --user-name <username>

# Undo
aliyun ram detach-policy-from-user \
  --policy-name AliyunSTSAssumeRoleAccess \
  --policy-type System \
  --user-name <username>
```

If role name is unknown, list roles first:
```bash
aliyun ram list-roles
```

---

## Service-Linked Role Commands

```bash
# Create a service-linked role
aliyun resourcemanager create-service-linked-role \
  --service-name <service>.aliyuncs.com

# Check whether a service-linked role exists
aliyun ram get-role --role-name AliyunServiceRole<ServiceName>
```

---

## CP Control Policy Query Commands (ResourceDirectory)

```bash
# List all control policies
aliyun resourcemanager list-control-policies

# View a specific control policy's content
aliyun resourcemanager get-control-policy --policy-id <policy-id>
```
