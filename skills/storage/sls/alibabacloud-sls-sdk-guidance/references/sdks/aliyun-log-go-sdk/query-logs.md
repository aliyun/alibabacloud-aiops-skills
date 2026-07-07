# Query Logs — aliyun-log-go-sdk

## Overview

Use `GetLogsV2` to run an index query over a time range — plain keyword/field search, or search plus SQL analysis (`... | select ...`).

## Docs

- Query syntax: https://help.aliyun.com/zh/sls/query-and-analyze-logs-in-index-mode
- Paged query: https://help.aliyun.com/zh/sls/paged-query
- API parameters (GetLogsV2): https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getlogsv2

## Example

```go
package main

import (
    "fmt"
    "os"
    "time"

    sls "github.com/aliyun/aliyun-log-go-sdk"
)

func main() {
    provider := sls.NewStaticCredentialsProvider(
        os.Getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
        os.Getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"), "")
    client := sls.CreateNormalInterfaceV2("cn-hangzhou.log.aliyuncs.com", provider)

    now := time.Now().Unix()
    req := &sls.GetLogRequest{
        From:  now - 3600, // unix seconds
        To:    now,
        Query: "level: ERROR | select count(*) as cnt",
        Lines: 100,
        Offset: 0,
    }
    resp, err := client.GetLogsV2("your_project", "your_logstore", req)
    if err != nil {
        panic(err)
    }
    for _, row := range resp.Logs { // resp.Logs is []map[string]string
        fmt.Println(row)
    }
}
```

## Paged Query

A single request returns at most `Lines` rows (max 100). For a plain search query,
page through results by advancing `Offset` until a short page comes back:

```go
offset := int64(0)
lines := int64(100)
for {
    req := &sls.GetLogRequest{From: from, To: to, Query: "level: ERROR", Lines: lines, Offset: offset}
    resp, err := client.GetLogsV2("your_project", "your_logstore", req)
    if err != nil {
        panic(err)
    }
    for _, row := range resp.Logs {
        fmt.Println(row)
    }
    if int64(len(resp.Logs)) < lines {
        break // last page reached
    }
    offset += lines
}
```

> `Offset`/`Lines` paging applies to **search** queries. For **SQL analysis**
> queries, page inside the SQL with `LIMIT offset, count` instead — see the
> paged-query doc above.
