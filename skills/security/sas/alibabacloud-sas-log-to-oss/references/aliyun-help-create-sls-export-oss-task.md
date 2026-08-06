After Log Service collects data, it supports shipping data to OSS Buckets for storage and analysis. This article describes the steps to create an OSS export task (new version).

## Prerequisites

-   A Project and LogStore have been created. For more information, see [Create a Project and LogStore](https://help.aliyun.com/zh/sls/getting-started#section-2l7-ol2-zro).

-   Data has been collected. For more information, see [Data Collection](https://help.aliyun.com/zh/sls/data-collection-overview#concept-ikm-ql5-vdb).

-   A Bucket has been created in the same region as the Log Service Project. For more information, see [Create a Bucket in the console](https://help.aliyun.com/zh/oss/getting-started/create-buckets-6#task-u3p-3n4-tdb).


## Supported Regions

Log Service ships data to OSS within the same region, meaning the Log Service Project and OSS Bucket must be in the same region.

**Important**

Currently supported regions include: China (Hangzhou), China (Shanghai), China (Nanjing - local region - shutting down), China (Hangzhou) Finance Cloud, China (Shanghai) Finance Cloud, China (Qingdao), China (Beijing), China (Zhangjiakou), China (Hohhot), China (Ulanqab), China (Chengdu), China (Shenzhen), China (Heyuan), China (Guangzhou), China (Hong Kong), Singapore, Malaysia (Kuala Lumpur), Indonesia (Jakarta), Philippines (Manila), Thailand (Bangkok), Japan (Tokyo), US (Silicon Valley), US (Virginia).

Among these, China (Hangzhou) Finance Cloud only supports OSS Buckets on the public network of China (Hangzhou) Finance Cloud; China (Shanghai) Finance Cloud only supports OSS Buckets of China (Shanghai) Finance Cloud.

## Create an Export Task

1.  Log in to the [Log Service console](https://sls.console.aliyun.com).

2.  In the Project list area, click the target Project.

    ![image](https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/8797827471/p955209.png)

3.  On the **Log Storage** > **Logstore** tab, click the **>** to the left of the target LogStore, then select **Data Processing** > **Export** > **OSS (Object Storage)**.

4.  Hover over **OSS (Object Storage)** and click **+**.

5.  In the **OSS Export** panel, configure the following parameters, then click **OK**.

    Select **Export Version** as **New Version**. Key parameter descriptions are as follows.

    **Important**

    -   After creating an OSS export task, each Shard determines the export frequency based on export size and export time. When either condition is met, an export is performed.

    -   After creating an OSS export task, you can verify whether the task meets expectations by checking the task status and the data exported to OSS.


    | **Parameter** | **Description** |
    | --- | --- |
    | **Task Name** | The unique name of the export task. |
    | **Display Name** | The display name of the export task. |
    | **Task Description** | The description of the OSS task. |
    | **OSS Bucket** | The OSS Bucket name. **Important** - Must be an existing Bucket without WORM enabled, and the Bucket must be in the same region as the Log Service Project. For more information about WORM, see [Bucket-level Retention Policy (BucketWorm)](https://help.aliyun.com/zh/oss/user-guide/oss-retention-policies). - Supports shipping to Buckets with Standard, Infrequent Access, Archive, Cold Archive, and Deep Cold Archive storage types. After shipping, the generated OSS Object storage type defaults to the same as the Bucket. For more information, see [Storage Types](https://help.aliyun.com/zh/oss/user-guide/overview-53/#concept-fcn-3xt-tdb). - Non-standard storage Buckets have minimum storage duration and minimum metering unit limits. Set the target Bucket storage type appropriately based on your needs. For more information, see [Storage Type Comparison](https://help.aliyun.com/zh/oss/user-guide/overview-53/#section-tbz-dt6-bg2). |
    | **File Export Directory** | The directory in the OSS Bucket. The directory name cannot start with a forward slash (/) or backslash (\\). After creating the OSS export task, data from the LogStore will be exported to this directory in the target OSS Bucket. |
    | **File Suffix** | If you do not set a file suffix, Log Service will automatically generate one based on the storage format and compression type. For example, `.suffix`. |
    | **Partition Format** | Dynamically generates the OSS Bucket directory based on export time. Cannot start with a forward slash (/). Default value is %Y/%m/%d/%H/%M. For examples, see [Partition Format](#section-ytg-xbb-idc). For parameter details, see [strptime API](https://man7.org/linux/man-pages/man3/strptime.3.html). |
    | **Write OSS RAM Role** | Grants the OSS export task permission to write data to the OSS Bucket. - **Default Role**: Authorizes the OSS export task to use the Alibaba Cloud system role AliyunLogDefaultRole to write data to the OSS Bucket. Enter the ARN of AliyunLogDefaultRole. For how to obtain the ARN, see [Access Data via Default Role](https://help.aliyun.com/zh/sls/access-data-by-using-a-default-role-3#task-2156395). - **Custom Role**: Authorizes the OSS export task to use a custom role to write data to the OSS Bucket. You must first grant the custom role permission to write to the OSS Bucket, then enter the ARN of your custom role in **Write OSS RAM Role**. For how to obtain the ARN: - If the LogStore and OSS Bucket belong to the same Alibaba Cloud account, see [Step 2: Grant the RAM Role Permission to Write to the OSS Bucket](https://help.aliyun.com/zh/sls/access-data-within-an-alibaba-cloud-account-by-using-a-custom-role#section-ikl-v3l-16u). - If the LogStore and OSS Bucket belong to different Alibaba Cloud accounts, see [Step 2: Grant RAM Role role-b under Account B Permission to Write to the OSS Bucket](https://help.aliyun.com/zh/sls/access-data-across-alibaba-cloud-accounts-by-using-a-custom-role#section-jwj-z1h-6do). |
    | **Read LogStore RAM Role** | Grants the OSS export task permission to read LogStore data. - **Default Role**: Authorizes the OSS export task to use the Alibaba Cloud system role AliyunLogDefaultRole to read data from the LogStore. Enter the ARN of AliyunLogDefaultRole. For how to obtain the ARN, see [Access Data via Default Role](https://help.aliyun.com/zh/sls/access-data-by-using-a-default-role-3#task-2156395). - **Custom Role**: Authorizes the OSS export task to use a custom role to read data from the LogStore. You must first grant the custom role permission to read LogStore data, then enter the ARN of your custom role in **Read LogStore RAM Role**. For how to obtain the ARN: - If the LogStore and OSS Bucket belong to the same Alibaba Cloud account, see [Step 1: Grant the RAM Role Permission to Read LogStore Data](https://help.aliyun.com/zh/sls/access-data-within-an-alibaba-cloud-account-by-using-a-custom-role#section-va5-c3b-801). - If the LogStore and OSS Bucket belong to different Alibaba Cloud accounts, see [Step 1: Grant RAM Role role-a under Account A Permission to Read LogStore Data](https://help.aliyun.com/zh/sls/access-data-across-alibaba-cloud-accounts-by-using-a-custom-role#section-0uy-54e-929). |
    | **Storage Format** | After data is exported to OSS, it supports being stored in different file formats. For more information, see [CSV Format](https://help.aliyun.com/zh/sls/csv-format#concept-hch-k4q-zdb), [JSON Format](https://help.aliyun.com/zh/sls/json-format-3#concept-2156388), [Parquet Format](https://help.aliyun.com/zh/sls/parquet-format-3#concept-2156390), and [ORC Format](https://help.aliyun.com/zh/sls/orc-format#concept-2184929). |
    | **Compression** | The compression method for OSS data storage. - No compression (none): Do not compress data. - Compress (snappy): Use the snappy algorithm to compress data, reducing OSS Bucket space. For more information, see [snappy](https://github.com/google/snappy/blob/main/README.md). - Compress (zstd): Use the zstd algorithm to compress data, reducing OSS Bucket space. - Compress (gzip): Use the gzip algorithm to compress data, reducing OSS Bucket space. |
    | **Export tag** | The tag field is a reserved field of Log Service. For more information, see [Reserved Fields](https://help.aliyun.com/zh/sls/reserved-fields). |
    | **Buffer Size** | Each Shard starts exporting when the accumulated log volume reaches the specified size. This value controls the OSS Object size (calculated as uncompressed). The range is 5-256, in MB. **Note** Buffer size refers to the buffer size after data starts being read, not the size of data already written to SLS. Data reading and exporting only begins after the buffer time configuration is met. |
    | **Buffer Interval** | The Shard log export rule: when the time difference between the first log arriving at the server and the nth log arriving is greater than or equal to the set value (default 300 seconds, range 300-900 seconds), exporting begins. |
    | **Delivery Delay** | The delay time for data delivery. For example, if set to 3600, data is delayed by 1 hour, meaning data from 2023/06/05 10:00:00 will not be written to the specified OSS Bucket before 2023/06/05 11:00:00. For related limit descriptions, see [Configuration Item Limits](https://help.aliyun.com/zh/sls/stability-and-limits-of-oss-data-shipping#a4af5d47b1wbh). |
    | **Time Range** | Specifies the time range of the OSS export task. The time range here depends on the log receive time. Detailed descriptions: - All: Start data export from the time the LogStore received the first log, until the export task is manually stopped. - From a specific time: Specify the start time of the OSS export task. Data export starts from that time point until the export task is manually stopped. - Specific time range: Specify the start and end time of the OSS export task. The export task automatically stops when it reaches the specified end time. **Note** The time range refers to `__tag__:__receive_time__`. For more details, see [Reserved Fields](https://help.aliyun.com/zh/sls/reserved-fields#concept-adr-ktr-gfb). |
    | **Timezone** | This timezone is used for time formatting. If you set both **Timezone** and **Partition Format**, the system will generate the OSS Bucket directory based on your settings. |


## View OSS Data

After data is successfully exported to OSS, you can access OSS data through the OSS console, API, SDK, or other methods. For more information, see [File Management](https://help.aliyun.com/zh/oss/upload-download-and-manage-objects-overview#concept-jft-vhg-vdb).

The OSS Object address format is as follows:

```
oss://OSS-BUCKET/OSS-PREFIX/PARTITION-FORMAT_RANDOM-ID
```

Where `OSS-BUCKET` is the OSS Bucket name, `OSS-PREFIX` is the directory prefix, `PARTITION-FORMAT` is the partition format (calculated from the export time via the [strptime API](https://man7.org/linux/man-pages/man3/strptime.3.html)), and `RANDOM-ID` is a unique identifier for one export operation.

**Note**

OSS export is performed in batches. Each batch writes one file containing a batch of data. The file path is determined by the smallest receive_time (the time data arrived at Log Service) in that batch. Note the following two scenarios:

-   When exporting real-time data (assuming export every 5 minutes), for example, an export at 2022-01-22 00:00:00 exports data written to a Shard after 2022-01-21 23:55. Therefore, if you want to analyze data for the entire day of 2022-01-22, you need to check all Objects under the 2022/01/22 directory in the OSS Bucket, and also check whether the last few Objects under the 2022/01/21 directory contain data from 2022-01-22.

-   When exporting historical data, if the data volume in the LogStore is relatively small, one data pull by the export task may contain multiple days of data, causing files under the 2022/01/22 directory to contain data for the entire day of 2022-01-23, while the 2022/01/23 directory has no files.


## Partition Format

One export corresponds to one OSS Object address, in the format oss://OSS-BUCKET/OSS-PREFIX/PARTITION-FORMAT\_RANDOM-ID. Using an export task created at 2022/01/20 19:50:43 as an example, the partition format is described in the table below.

| **OSS Bucket** | **OSS Prefix** | **Partition Format** | **File Suffix** | **OSS File Path** |
| --- | --- | --- | --- | --- |
| test-bucket | test-table | %Y/%m/%d/%H/%M | .suffix | oss://test-bucket/test-table/2022/01/20/19/50\\_1484913043351525351\\_2850008.suffix |
| test-bucket | log\\_ship\\_oss\\_example | year=%Y/mon=%m/day=%d/log\\_%H%M | .suffix | oss://test-bucket/log\\_ship\\_oss\\_example/year=2022/mon=01/day=20/log\\_1950\\_1484913043351525351\\_2850008.suffix |
| test-bucket | log\\_ship\\_oss\\_example | ds=%Y%m%d/%H | .suffix | oss://test-bucket/log\\_ship\\_oss\\_example/ds=20220120/19\\_1484913043351525351\\_2850008.suffix |
| test-bucket | log\\_ship\\_oss\\_example | %Y%m%d/ | .suffix | oss://test-bucket/log\\_ship\\_oss\\_example/20220120/\\_1484913043351525351\\_2850008.suffix **Note** This format will cause platforms like Hive to be unable to parse the corresponding OSS content. It is recommended not to use this format. |
| test-bucket | log\\_ship\\_oss\\_example | %Y%m%d%H | .suffix | oss://test-bucket/log\\_ship\\_oss\\_example/2022012019\\_1484913043351525351\\_2850008.suffix |

When using big data platforms such as Hive, MaxCompute, or Alibaba Cloud DLA to analyze OSS data, if you want to use Partition information, you can set the PARTITION-FORMAT in the file name to key=value format. For example: oss://test-bucket/log\_ship\_oss\_example/year=2022/mon=01/day=20/log\_195043\_1484913043351525351\_2850008.parquet, setting three levels of partition columns: year, mon, day.

## SDK Example

[Create OSS Export Task](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-createossexport)
