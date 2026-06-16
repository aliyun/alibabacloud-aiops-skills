# Alibaba Cloud Realtime Compute for Apache Flink — Quick Start Guide

## Activating Realtime Compute for Apache Flink

1. Log in to the [Realtime Compute Console](https://realtime-compute.console.aliyun.com/)
2. Select the target region
3. Create a Flink workspace (choose storage type: fully managed / OSS Bucket)
4. Select a billing mode

## Flink SQL Job Quick Start

### Complete Workflow: 5 Steps to Get Started

**Step 1: Create a Job**
```
Console → Data Development → ETL → New Stream Job → Enter Name → Select Engine Version
```

**Step 2: Write SQL (Datagen → Print)**
```sql
-- Create a temporary source table (random data generator)
CREATE TEMPORARY TABLE datagen_source(
  randstr VARCHAR
) WITH (
  'connector' = 'datagen'
);

-- Create a temporary result table (console print)
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

**Step 3: Deep Inspection & Debug**
- Click **Deep Inspection**: Checks SQL semantics and network connectivity
- Click **Debug**: Simulates execution to verify output results (does not write downstream)

**Step 4: Deploy**
- Click **Deploy** → Select deployment target (resource queue / Session cluster) → Confirm

**Step 5: Start & Verify**
- **O&M Center > Job O&M** → Start → Stateless Start → Confirm
- Search for `PrintSinkOutputWriter` in Task Managers logs to verify results

## JAR Job Quick Start

Use cases: complex business logic, custom operators, CEP, DataStream API.

```
Console → Data Development → New Stream Job → Select JAR type
→ Upload JAR package (with dependencies)
→ Configure Main Class and parameters
→ Deploy → Start
```

## Python Job Quick Start

Use cases: data analysis, machine learning integration, Python ecosystem users.

```
Console → Data Development → New Stream Job → Select Python type
→ Write PyFlink code
→ Deploy → Start
```

## Data Sync Quick Start

### Real-Time Database Ingestion

MySQL / PostgreSQL / Oracle → Flink → Hologres / StarRocks

```
Console → Data Sync Template → Select target scenario → One-click generation
```

### Real-Time Log Ingestion

SLS Logs → Flink → MaxCompute / Paimon

### Real-Time Data Lake Ingestion Based on Paimon

MySQL CDC → Flink → Paimon streaming data lake

## AI Integration: Real-Time Data Analysis Based on Large Models

Flink supports integration with Alibaba Cloud Model Studio and other large model platforms:

```sql
-- Call large model API in SQL
SELECT llm_generate(prompt) AS llm_result
FROM (
    SELECT CONCAT('Analyze the sentiment of the following user review:', comment_text) AS prompt
    FROM user_comments
);
```

## Code Templates

The console provides rich pre-built code templates covering common scenarios:
- Kafka consumption & writes
- MySQL CDC sync
- Window aggregation statistics
- Dimension table joins
- Dual-stream JOIN

## Recommended Learning Path

```
Recommended path for beginners:
1. Activate a workspace
2. Use the Datagen+Print template to experience the SQL workflow (10 minutes)
3. Connect real Kafka or MySQL CDC data
4. Configure monitoring and alerts
5. Use smart tuning to optimize resources
6. Explore CDAS/CTAS full-database sync
7. Evaluate AI integration scenarios
```

## Official Documentation Links

- [Activate Realtime Compute for Apache Flink](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/activate-fully-managed-flink)
- [Flink SQL Job Quick Start](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/getting-started-for-a-flink-sql-deployment)
- [Flink JAR Job Quick Start](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/getting-started-for-a-flink-jar-deployment)
- [Flink Python Job Quick Start](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/getting-started-for-a-flink-python-deployment)
- [Real-Time Database Ingestion Quick Start](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/ingest-data-into-data-warehouses-in-real-time)
- [Real-Time Log Ingestion Quick Start](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/ingest-log-data-into-data-warehouses-in-real-time)
- [Paimon-Based Real-Time Data Lake Ingestion Quick Start](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/getting-started-for-real-time-data-ingestion-into-data-lakes-based-on-apache-paimon)
- [Large Model Integration Quick Start](https://help.aliyun.com/zh/flink/realtime-flink/getting-started/integrate-with-alibaba-cloud-model-studio)
- [Experience with Built-in Public Datasets](https://help.aliyun.com/zh/flink/getting-started/use-built-in-public-datasets-to-experience-realtime-compute-for-apache-flink)
