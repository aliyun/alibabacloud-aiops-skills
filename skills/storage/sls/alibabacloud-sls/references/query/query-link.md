# Console query links

Run from the skill root to generate a Logstore console query link for the last hour:

```bash
python3 scripts/query/generate_query_link.py \
  --project test-project --logstore test-logstore \
  --query '* | SELECT count(*) AS total' --range 3600
```

Example output (test resource names):

```text
https://sls.console.aliyun.com/lognext/project/test-project/logsearch/test-logstore?encode%3Dbase64%26queryString%3DKiB8IFNFTEVDVCBjb3VudCgqKSBBUyB0b3RhbA%3D%3D%26queryTimeType%3D99%26startTime%3D1794646535%26endTime%3D1794650135
```

| Parameter | Description |
| --- | --- |
| `--project` | Required. Project name. |
| `--logstore` | Required. Logstore name. |
| `--query` | Required. Original query statement. |
| `--range` | Last N seconds, a positive integer. Defaults to 900 (15 minutes). |
| `--from`, `--to` | Optional absolute start and end, as non-negative Unix timestamps in seconds. Supply both with `--from < --to`; cannot combine with `--range`. |

Return the generated URL as a clickable link. The time window stays fixed when the link is reopened.
