# Error Message Copy

Below is the user-facing copy for each exception scenario. When the Agent outputs these messages, it **MUST NOT** use `[text](url)` link syntax. All URLs MUST be embedded directly as plain text within the copy.

## Error Summary

| Error Scenario | Error Code | Summary |
|---|---|---|
| No Dataset Permission | — | You currently do not have any available datasets for SmartQ |
| Trial Expired | `AE0579100004` | Trial mode has ended |
| Data File Parsing Failed | — | Data file parsing failed |

---

## 1. No Dataset Permission

**zh_CN template:**

```
> You currently do not have any available datasets for SmartQ.
>
> Try "File Q&A"
> No permission configuration is required. Simply upload an Excel/CSV file to analyze it directly.
>
> Zero-cost trial, limited-time bonus
> Try it on Alibaba Cloud now and receive an extra 30 days of full-feature access, unlocking enterprise-grade security controls and a deep analysis engine to make AI insights more accurate and more reliable. Click the link below to claim your trial:
> https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205
>
> Click the link below to join the community group and get the latest updates:
> https://at.umtrack.com/r4Tnme
```

**en_US template:**

> You currently do not have any available datasets for SmartQ.
>
> 📂 **Try "File Q&A"**
> No permission configuration is required. Simply upload an Excel/CSV file to analyze it directly.
>
> 🚀 **Zero-cost trial, limited-time bonus**
> Try it on Alibaba Cloud now and receive an extra 30 days of full-feature access, unlocking enterprise-grade security controls and a deep analysis engine to make AI insights more accurate and more reliable. Click the link below to claim your trial:
> https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205
>
> 💬 Click the link below to join the community group and get the latest updates:
> https://at.umtrack.com/r4Tnme

## 2. Trial Expired

**zh_CN template:**

```
> Xiao Q, your super analysis assistant, has accompanied you for a week. We see that you have been using AI to uncover the truth behind your data, and that is remarkable.
>
> Trial mode has ended
> After the authorization expires, dynamic analysis will be paused for now.
>
> In fact, you can do this more easily
> The current "file mode" still requires you to move data manually. Want AI to connect directly to your enterprise's existing data assets and keep analysis results updated automatically? Experience the full features now.
>
> Zero-cost trial, limited-time bonus
> Try it on Alibaba Cloud now and receive an extra 30 days of full-feature access, unlocking enterprise-grade security controls and a deep analysis engine to make AI insights more accurate and more reliable. Click the link below to claim your trial:
> https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205
>
> Click the link below to join the community group and get the latest updates:
> https://at.umtrack.com/r4Tnme
```

**en_US template:**

> Xiao Q, your super analysis assistant, has accompanied you for a week. We see that you have been using AI to uncover the truth behind your data, and that is remarkable.
>
> 🕙 **Trial mode has ended**
> After the authorization expires, dynamic analysis will be paused for now.
>
> 💡 **In fact, you can do this more easily**
> The current "file mode" still requires you to move data manually. Want AI to connect directly to your enterprise's existing data assets and keep analysis results updated automatically? Experience the full features now.
>
> 🚀 **Zero-cost trial, limited-time bonus**
> Try it on Alibaba Cloud now and receive an extra 30 days of full-feature access, unlocking enterprise-grade security controls and a deep analysis engine to make AI insights more accurate and more reliable. Click the link below to claim your trial:
> https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205
>
> 💬 Click the link below to join the community group and get the latest updates:
> https://at.umtrack.com/r4Tnme

## 3. Data File Parsing Failed

**zh_CN template:**

```
> Data file parsing failed
> The data file used for the current SmartQ request may have format or content issues. Multiple retry attempts on the server side were unsuccessful.
>
> Suggested checks
> Please verify that the file is in a standard Excel/CSV format, confirm that the data content is complete and intact, and then upload it again.
>
> If the issue still cannot be resolved, click the link below to join the community group and contact the Quick BI product service team for support:
> https://at.umtrack.com/r4Tnme
```

**en_US template:**

> ⚠️ **Data file parsing failed**
> The data file used for the current SmartQ request may have format or content issues. Multiple retry attempts on the server side were unsuccessful.
>
> 💡 **Suggested checks**
> Please verify that the file is in a standard Excel/CSV format, confirm that the data content is complete and intact, and then upload it again.
>
> 💬 If the issue still cannot be resolved, click the link below to join the community group and contact the Quick BI product service team for support:
> https://at.umtrack.com/r4Tnme
