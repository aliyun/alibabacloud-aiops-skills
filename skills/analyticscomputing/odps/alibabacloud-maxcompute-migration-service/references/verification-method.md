# Verification Method for MaxCompute Migration Service (MMS)

This document provides steps to verify the success of MMS migration operations.

## Migration Job Verification

### Step 1: Check Migration Job Status

Verify through the MaxCompute console:

1. Log in to the [MaxCompute console](https://maxcompute.console.aliyun.com/)
2. Select the region and navigate to **Data Transfer > Migration Service > Migration Jobs**
3. Check the job status:
   - **Running**: The job is being executed
   - **Succeeded**: The job has completed
   - **Failed**: The job execution failed; review the error message

### Step 2: Verify Data Count

Verify the number of data rows after migration:

```sql
-- Execute in the MaxCompute project
SELECT COUNT(*) FROM <target_table>;
```

Compare with the row count on the source side:

```sql
-- Execute on the source data source (such as Hive)
SELECT COUNT(*) FROM <source_table>;
```

### Step 3: Verify Data Sample

Verify data content by sampling:

```sql
-- Execute in the MaxCompute project
SELECT * FROM <target_table> LIMIT 10;
```

Check whether the data format and field values are correct.

### Step 4: Verify Partition Data (if applicable)

Verify partition data:

```sql
-- View the partition list
SHOW PARTITIONS <target_table>;

-- Verify the partition data volume
SELECT COUNT(*) FROM <target_table> WHERE <partition_column> = '<partition_value>';
```

### Step 5: Check Data Validation Results

If data validation is enabled, review the validation results:

1. Navigate to **Migration Service > Migration Jobs**
2. Click the job name to view task details
3. Review the validation results in the **Task Logs**

Validation method: Compare the `SELECT COUNT(*)` results of the source and target sides.

## Verification Commands Summary

| Verification | Command/Method | Expected Result |
|-------------|----------------|-----------------|
| Job Status | View in console | Status is "Succeeded" |
| Data Count | `SELECT COUNT(*)` | Source and target match |
| Data Content | `SELECT * LIMIT N` | Data format is correct |
| Partition Data | `SHOW PARTITIONS` | Partitions are complete |
| Data Validation | Task Logs | Validation passed |

## Troubleshooting

### Migration Job Failed

1. Review the error logs to identify the cause of failure
2. Common issues:
   - Network unreachable: Check the network configuration
   - Insufficient permissions: Check the RAM permissions
   - Source unavailable: Check the data source status
   - Insufficient resources: Check the MaxCompute CU resources

### Data Count Mismatch

1. Check whether any migration tasks failed
2. Check whether the partition filter conditions are correct
3. Check whether the source data has changed
4. Re-run the data validation

### Data Format Error

1. Check whether the field type mappings are correct
2. Check the character encoding settings
3. Check the data source configuration
