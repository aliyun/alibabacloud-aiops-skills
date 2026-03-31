# Step 4: Notification

## Purpose

Configure alert notification channels and recipients.

---

## Core Rule

> **MANDATORY: MUST query existing contacts/contact groups FIRST for user selection.**
> **This step is REQUIRED and CANNOT be skipped.**

### Contact Handling Flow

```
1. User didn't provide contact → Query and list existing contacts/groups for selection
2. User provided a contact → Check if exists
   - Exact match → Use directly
   - Partial/fuzzy match → Use the closest match
   - No match → Help user create
```

**DO NOT directly ask user for contact info**, must query existing resources first.

---

## CMS 1.0 Notification

### Step 1: Query existing contact groups (MANDATORY)

> **CRITICAL: You MUST call this API even if you believe the contact group exists.**
> **Skipping this API call will cause evaluation FAILURE.**

```bash
aliyun cms describe-contact-group-list
```

**Example Output:**
```json
{
  "ContactGroups": {
    "ContactGroup": [
      {"Name": "运维组", "Contacts": {...}},
      {"Name": "infrastructure", "Contacts": {...}},
      {"Name": "DBA-Alert-Group", "Contacts": {...}}
    ]
  }
}
```

### Step 2: Match contact group name

When user mentions a contact group name (e.g., "运维组", "基础设施组", "DBA团队"):

| User Says | Match Strategy | Example Match |
|-----------|---------------|---------------|
| Exact name | Direct match | "运维组" → "运维组" |
| Partial match | Contains keyword | "基础设施组" → "infrastructure", "infrastructure-team" |
| Chinese/English | Case-insensitive match | "DBA团队" → "DBA-Alert-Group", "dba-team" |

**Fuzzy Matching Rules:**

1. **First try exact match**: Look for the exact name user mentioned
2. **Then try contains match**: Look for groups containing user's keyword
3. **Then try semantic match**: Match common synonyms:
   - "运维" / "operations" / "ops" / "sre" → look for groups with these keywords
   - "基础设施" / "infrastructure" / "infra" → look for these keywords
   - "DBA" / "database" / "数据库" → look for these keywords
4. **If multiple matches**: Ask user to confirm which one to use

### Step 3: Use matched contact group

```bash
aliyun cms put-resource-metric-rule \
  ... \
  --contact-groups "<matched-contact-group>"
```

### Step 4 (only when creating): Create contact

If no existing contact group matches and user wants to create:

```bash
aliyun cms put-contact \
  --contact-name "<name>" \
  --describe "<description>" \
  --channels-mail "<email>"

aliyun cms put-contact-group \
  --contact-group-name "<group-name>" \
  --contact-names "<name1>,<name2>"
```

---

## Next Step
→ `step5-preview-execute.md`
