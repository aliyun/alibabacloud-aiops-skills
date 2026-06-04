# OOS Template Verification Method

## 1. Validate Using CLI validate-template-content

This is the most direct and recommended verification method:

```bash
# Write the template to a temp file
cat > /tmp/oos_template.yaml << 'EOF'
<template content>
EOF

# Call CLI to validate
aliyun oos validate-template-content \
  --biz-region-id cn-hangzhou \
  --content "$(cat /tmp/oos_template.yaml)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation
```

Response:
- Validation passed: Returns `RequestId` with no error message
- Validation failed: Returns error with `Code` and `Message`, fix the template based on the error

## 2. CLI Verification

### Verify by Creating Template via CLI

```bash
# Attempt to create a template — syntax errors will return error messages
aliyun oos create-template \
  --template-name "TestTemplate_$(date +%s)" \
  --content "$(cat /tmp/oos_template.yaml)" \
  --biz-region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation
```

### Verify Response

On success:
```json
{
  "Template": {
    "TemplateName": "TestTemplate_xxx",
    "CreatedDate": "2024-01-01T00:00:00Z",
    ...
  },
  "RequestId": "xxx"
}
```

On failure, error messages are returned to help locate the issue.

## 3. Common Validation Errors and Fixes

### Error: Invalid Action

**Error message**: `InvalidAction: Action "xxx" is not valid`

**Fix**:
1. Search for the correct Action name using CLI:
```bash
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --oos-action-name "<keyword>" \
  --max-results 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation
```
2. Replace with the correct Action

### Error: Invalid Parameter

**Error message**: `InvalidParameter: Property "xxx" is required`

**Fix**:
1. Get the complete property definitions of the Action using CLI:
```bash
aliyun oos list-actions \
  --biz-region-id cn-hangzhou \
  --oos-action-name "<exact Action name>" \
  --max-results 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oos-template-generation
```
2. Check the property definitions in `Actions[0].Properties` of the response
3. Add the missing required properties

### Error: Invalid Reference

**Error message**: `InvalidReference: Task output "xxx" is not defined`

**Fix**:
1. Check whether the referenced Task has defined Outputs
2. Add the Outputs definition to the referenced Task

### Error: Invalid FormatVersion

**Error message**: `InvalidFormatVersion: FormatVersion must be OOS-2019-06-01`

**Fix**:
Ensure FormatVersion is set to `OOS-2019-06-01`

## 4. Verification Checklist

Before outputting the template, confirm the following items:

- [ ] FormatVersion is `OOS-2019-06-01`
- [ ] Description includes both en and zh-cn bilingual content
- [ ] All Task Names use English naming
- [ ] Parameter reference format is `{{ paramName }}` (double curly braces + spaces)
- [ ] Referenced Task outputs are defined in the corresponding Task
- [ ] No non-existent Actions (e.g., ACS::Flow::ForEach)
- [ ] Property name case matches the Action definition
- [ ] CLI validate-template-content returns no errors
