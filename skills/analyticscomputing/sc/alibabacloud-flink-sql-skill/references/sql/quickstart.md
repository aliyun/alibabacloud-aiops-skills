# Flink SQL Quickstart

## Flink SQL Job Quickstart

### Complete Flow: Start in Five Steps

**Step 1: Create a Job**

```text
Console → Data Development → ETL → Create Streaming Job → Enter Name → Select Engine Version
```

**Step 2: Write SQL (Datagen → Print)**

```sql
-- Create a temporary Source Table (random data generator)
CREATE TEMPORARY TABLE datagen_source(
  randstr VARCHAR
) WITH (
  'connector' = 'datagen'
);

-- Create a temporary Sink Table (write to the console)
CREATE TEMPORARY TABLE print_table(
  randstr VARCHAR
) WITH (
  'connector' = 'print',
  'logger' = 'true'
);

-- Write results
INSERT INTO print_table
SELECT SUBSTRING(randstr, 0, 8) FROM datagen_source;
```

**Step 3: Deep Check and Debug**

- Click **Deep Check** to check SQL semantics and network connectivity.
- Click **Debug** to simulate execution and verify output without writing to the downstream system.

**Step 4: Deploy**

- Click **Deploy**, select a Deployment Target (Resource Queue / Session Cluster), and confirm.

**Step 5: Start and Verify**

- Go to **Operations Center → Job Operations**, click **Start**, select **Stateless Start**, and confirm.
- Search TaskManager logs for `PrintSinkOutputWriter` to verify output.

## Data Synchronization Quickstart

### Real-Time Database Ingestion into a Data Warehouse

MySQL / PostgreSQL / Oracle → Flink → Hologres / StarRocks

```text
Console → Data Development → ETL → Generate and Review CDAS/CTAS SQL → Validate → Deploy
```

### Real-Time Log Ingestion into a Data Warehouse

SLS logs → Flink → MaxCompute / Paimon

### Real-Time Data-Lake Ingestion with Paimon

MySQL CDC → Flink → Paimon real-time data lake

## AI Integration: Real-Time Data Analysis with Large Models

Flink supports large-model platforms such as Alibaba Cloud Model Studio:

```sql
-- Call a large-model API from SQL
SELECT llm_generate(prompt) AS llm_result
FROM (
    SELECT CONCAT('Analyze the sentiment of this user review: ', comment_text) AS prompt
    FROM user_comments
);
```

## Code Templates

The console provides templates for common use cases:

- Kafka reads and writes;
- MySQL CDC synchronization;
- Windowed aggregations;
- Dimension-table Joins;
- Stream-stream Joins.

## Recommended Learning Path

```text
Recommended path for beginners:
1. Confirm the target Workspace, Namespace, and local credential chain
2. Try the SQL workflow with a Datagen + Print template (about 10 minutes)
3. Connect to real Kafka or MySQL CDC data
4. Configure monitoring and alerts
5. Optimize resources with intelligent tuning
6. Explore whole-database CDAS/CTAS synchronization
7. Evaluate AI integration scenarios
```

## Official Documentation

- [Flink SQL Job Quickstart](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/getting-started-for-a-flink-sql-deployment)
- [Real-Time Database Ingestion into Data Warehouses](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/ingest-data-into-data-warehouses-in-real-time)
- [Real-Time Log Ingestion into Data Warehouses](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/ingest-log-data-into-data-warehouses-in-real-time)
- [Real-Time Data-Lake Ingestion with Apache Paimon](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/getting-started-for-real-time-data-ingestion-into-data-lakes-based-on-apache-paimon)
- [Large-Model Integration Quickstart](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/integrate-with-alibaba-cloud-model-studio)
- [Experience Flink with Built-In Public Data Sets](https://help.aliyun.com/zh/flink/getting-started/use-built-in-public-datasets-to-experience-realtime-compute-for-apache-flink)
