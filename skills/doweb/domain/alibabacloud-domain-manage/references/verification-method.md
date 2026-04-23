# Success Verification Method — Domain Query

## Scenario 1: Domain Query by Domain Name

**Expected Outcome**: Domain information displayed correctly from API response.

**Verification Command**:
```bash
aliyun domain query-domain-by-domain-name \
  --api-version 2018-01-29 \
  --domain-name "<domain-name>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage
```

**Success Indicator**: Returns JSON with `DomainName`, `ExpirationDate`, `DomainStatus` fields populated.

---

## Scenario 2: Domain Query by Instance ID

**Expected Outcome**: Domain information retrieved by instance ID.

**Verification Command**:
```bash
aliyun domain query-domain-by-instance-id \
  --api-version 2018-01-29 \
  --instance-id "<instance-id>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage
```

**Success Indicator**: Returns JSON with same structure as Scenario 1.

---

## Scenario 3: Domain List Query

**Expected Outcome**: Domain list retrieved with correct pagination.

**Verification Command**:
```bash
aliyun domain query-domain-list \
  --api-version 2018-01-29 \
  --page-num 1 \
  --page-size 5 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage
```

**Success Indicator**: Returns JSON with `TotalItemNum >= 0` and `Data` array.

---

## Scenario 4: Advanced Domain Search

**Expected Outcome**: Filtered domain list retrieved matching search criteria.

**Verification Command**:
```bash
aliyun domain query-advanced-domain-list \
  --api-version 2018-01-29 \
  --page-num 1 \
  --page-size 5 \
  --domain-status 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage
```

**Success Indicator**: Returns JSON with `TotalItemNum >= 0` and `Data` array containing only domains matching the filter.
