# SMS Qualification (短信资质) Query Reference

This document describes the two `dysmsapi` qualification query APIs supported by this
Skill. Both commands MUST honor the global compliance rules declared in
`SKILL.md` → `Critical CLI Compliance (Must Read First)`:

- aliyun CLI ≥ 3.3.3 with up-to-date plugins
- AI-Mode enabled before invocation, disabled at every exit
- `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message` on
  every CLI invocation
- `--read-timeout 3` and `--api-version 2017-05-25`

---

## 1. QuerySmsQualificationRecord — List Qualification Records

Query the list of SMS qualification records under the current account, including
audit details. Supports both full-list query (no filters) and conditional query.

> Use this API to discover the `GroupId` you need before calling
> `QuerySingleSmsQualification` for the full detail.

### CLI command

```bash
aliyun dysmsapi query-sms-qualification-record \
  --api-version 2017-05-25 \
  --page-no 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message \
  --read-timeout 3
```

### Parameters

| Parameter                    | Required | Description                                                                                          |
| ---------------------------- | -------- | ---------------------------------------------------------------------------------------------------- |
| --api-version                | Yes      | Fixed to `2017-05-25`                                                                                |
| --qualification-group-name   | No       | Qualification name filter                                                                            |
| --company-name               | No       | Company name filter                                                                                  |
| --state                      | No       | Audit state filter: `INIT` / `NOT_PASS` / `PASS` / `NOT_FINISH` / `CANCEL`                           |
| --work-order-id              | No       | Audit work-order ID filter                                                                           |
| --legal-person-name          | No       | Legal person name filter                                                                             |
| --use-by-self                | No       | `true` = self-use; `false` = used by others                                                          |
| --page-no                    | No       | Page number, starts from 1, defaults to 1                                                            |
| --page-size                  | No       | Page size, range 1~50, defaults to 20                                                                |
| --user-agent                 | Yes      | Fixed to `AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message`                             |
| --read-timeout               | Yes      | Read timeout in seconds, recommended value `3`                                                       |

### Filter examples

```bash
# Only approved (PASS) qualifications
aliyun dysmsapi query-sms-qualification-record \
  --api-version 2017-05-25 --state PASS --page-no 1 --page-size 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3

# By company name + self-use only
aliyun dysmsapi query-sms-qualification-record \
  --api-version 2017-05-25 \
  --company-name "Aliyun Communication Co., Ltd." --use-by-self true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3
```

### Response shape (key fields)

```json
{
  "Code": "OK",
  "Message": "OK",
  "RequestId": "25D5AFDE-...",
  "Success": true,
  "Data": {
    "PageNo": 1,
    "PageSize": 20,
    "Total": 25,
    "List": [
      {
        "GroupId": 10000123,
        "QualificationGroupName": "Aliyun Communication Co., Ltd. - LiHua",
        "CompanyName": "Aliyun Communication Co., Ltd.",
        "LegalPersonName": "LiHua",
        "WorkOrderId": 20011234,
        "StateName": "INIT",
        "AuditRemark": "N/A",
        "AuditTime": "2024-12-26 17:29:04",
        "CreateDate": "2025-02-20 11:59:30",
        "UseBySelf": true
      }
    ]
  }
}
```

### `StateName` enumeration (list API)

| Value         | Meaning                              |
| ------------- | ------------------------------------ |
| INIT          | Under review                         |
| PASS          | Approved (available for use)         |
| NOT_PASS      | Rejected (see `AuditRemark`)         |
| NOT_FINISH    | Pending supplement of materials      |
| CANCEL        | Withdrawn by the user                |

> If `StateName == NOT_PASS`, read `AuditRemark` to find out why and call the
> "Modify SMS qualification" API or fix it via the SMS console, then re-submit.

---

## 2. QuerySingleSmsQualification — Single Qualification Detail

Fetch the full detail (company / legal person / admin contact / business license
images / etc.) of one qualification by its `GroupId`. Use this AFTER you have
located the target qualification via `QuerySmsQualificationRecord`.

### CLI command

```bash
aliyun dysmsapi query-single-sms-qualification \
  --api-version 2017-05-25 \
  --qualification-group-id 10000123 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message \
  --read-timeout 3
```

### Parameters

| Parameter                    | Required | Description                                                                |
| ---------------------------- | -------- | -------------------------------------------------------------------------- |
| --api-version                | Yes      | Fixed to `2017-05-25`                                                      |
| --qualification-group-id     | Yes      | Qualification ID (`GroupId` returned by `query-sms-qualification-record`)  |
| --order-id                   | No       | Audit work-order ID                                                        |
| --user-agent                 | Yes      | Fixed to `AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message`   |
| --read-timeout               | Yes      | Read timeout in seconds, recommended value `3`                             |

### Response shape (key fields)

```json
{
  "Code": "OK",
  "Message": "OK",
  "RequestId": "25D5AFDE-...",
  "Success": true,
  "Data": {
    "QualificationGroupId": 10000123,
    "QualificationName": "Aliyun Communication Co., Ltd. - LiHua",
    "CompanyName": "Aliyun Communication Co., Ltd.",
    "CompanyType": "COMPANY",
    "OrganizationCode": "910X********0012",
    "LegalPersonName": "LiHua",
    "LegalPersonIDCardType": "identityCard",
    "LegalPersonIDCardNo": "511391********5123",
    "LegalPersonIdCardEffTime": "2023-01-01~2033-01-01",
    "AdminName": "LiHua",
    "AdminPhoneNo": "137*******",
    "AdminIDCardType": "identityCard",
    "AdminIDCardNo": "511391********5123",
    "AdminIDCardExpDate": "2023-01-01~2033-01-01",
    "AdminIDCardFrontFace": "https://...aliyuncs.com/...",
    "AdminIDCardPic": "https://...aliyuncs.com/...",
    "BusinessType": "dysms",
    "BusinessLicensePics": [
      { "Type": "businessLicense", "LicensePic": "123456/111.png",
        "PicUrl": "https://...aliyuncs.com/..." }
    ],
    "OtherFiles": [
      { "LicensePic": "123456/111.png", "PicUrl": "https://...aliyuncs.com/..." }
    ],
    "EffTimeStr": "2023-01-01~2033-01-01",
    "UseBySelf": false,
    "WhetherShare": false,
    "WorkOrderId": 20011234,
    "State": "PASSED",
    "Remark": "N/A"
  }
}
```

### `State` enumeration (single-detail API — note the values differ from list)

| Value         | Meaning                              |
| ------------- | ------------------------------------ |
| INT           | Under review                         |
| PASSED        | Approved                             |
| FAILED        | Rejected (call list API for remark)  |
| NOT_FINISH    | Pending supplement                   |
| CANCELED      | Withdrawn                            |

> The single-detail API does NOT return `AuditRemark`. To get the rejection
> reason, fall back to `QuerySmsQualificationRecord` filtered by
> `--work-order-id` of the same record.

---

## Typical workflow

```text
1. Call query-sms-qualification-record (--state PASS) to locate the target
   qualification, take its `GroupId`.
2. Call query-single-sms-qualification --qualification-group-id <GroupId>
   to fetch the full company / legal-person / admin / license detail.
3. If the list API shows StateName == NOT_PASS, read `AuditRemark` and either
   modify the qualification or open the SMS console to re-submit.
```

## Notes

1. **Audit windows** — qualification audits are processed Mon–Sun 09:00~21:00,
   typically within 2 working days. Be patient and re-query rather than
   re-submitting.
2. **State naming inconsistency** — `StateName` in the list API and `State` in
   the single-detail API use different vocabularies (`PASS` vs `PASSED`,
   `INIT` vs `INT`, `NOT_PASS` vs `FAILED`, `CANCEL` vs `CANCELED`). When
   correlating results across the two APIs, normalize them at the call-site.
3. **PII safety** — responses contain ID-card numbers, license images, admin
   phone numbers. Do NOT log them verbatim or echo them to the user without
   redaction; mask middle digits when displaying.
4. **Pagination** — `query-sms-qualification-record` uses `--page-no` /
   `--page-size` (max 50). Iterate pages until `Data.PageNo * Data.PageSize >=
   Data.Total` to walk the full list.
5. **RAM permissions** — both APIs require the calling RAM identity to hold
   read permission on `dysmsapi`. See `references/ram-policies.md`.

## References

- [QuerySmsQualificationRecord docs](https://help.aliyun.com/zh/sms/developer-reference/api-dysmsapi-2017-05-25-querysmsqualificationrecord)
- [QuerySingleSmsQualification docs](https://help.aliyun.com/zh/sms/developer-reference/api-dysmsapi-2017-05-25-querysinglesmsqualification)
