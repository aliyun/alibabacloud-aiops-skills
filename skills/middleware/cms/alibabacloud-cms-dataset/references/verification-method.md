# Verification Method: alibabacloud-cms-dataset

Steps to verify each workflow action was successful.

## 1. List Datasets

**Command:**
```bash
aliyun cms list-datasets --api-version 2024-03-30 --workspace <workspace>
```

**Success criteria:**
- HTTP 200 response
- Response contains `datasets` array
- Each entry has `datasetName`, `description`, and metadata

**Verification:**
- Check that `datasets` is present and is an array (may be empty for new workspaces)

## 2. Get Dataset

**Command:**
```bash
aliyun cms get-dataset --api-version 2024-03-30 --workspace <workspace> --dataset-name <name>
```

**Success criteria:**
- HTTP 200 response
- Response contains `datasetName`, `schema`, and `description`
- `schema` contains the expected field definitions

**Verification:**
- Confirm `datasetName` matches the requested name
- Confirm `schema` field keys match expected fields

## 3. Create Dataset

**Pre-check:**
```bash
aliyun cms list-datasets --api-version 2024-03-30 --workspace <workspace> --dataset-name <name>
```
- Verify dataset does NOT already exist

**Command:**
```bash
aliyun cms create-dataset --api-version 2024-03-30 --workspace <workspace> \
  --dataset-name <name> --schema '{"field":{"type":"text","chn":true}}'
```

**Success criteria:**
- HTTP 200 response with no error

**Post-verification:**
```bash
aliyun cms get-dataset --api-version 2024-03-30 --workspace <workspace> --dataset-name <name>
```
- Confirm the dataset exists and schema matches what was submitted

## 4. Update Dataset

**Pre-check:**
```bash
aliyun cms get-dataset --api-version 2024-03-30 --workspace <workspace> --dataset-name <name>
```
- Record current description

**Command:**
```bash
aliyun cms update-dataset --api-version 2024-03-30 --workspace <workspace> \
  --dataset-name <name> --description "new description"
```

**Post-verification:**
```bash
aliyun cms get-dataset --api-version 2024-03-30 --workspace <workspace> --dataset-name <name>
```
- Confirm description has been updated to the new value

## 5. Delete Dataset

**Pre-check:**
```bash
aliyun cms get-dataset --api-version 2024-03-30 --workspace <workspace> --dataset-name <name>
```
- Confirm the dataset exists and show details to user for confirmation

**Command:**
```bash
aliyun cms delete-dataset --api-version 2024-03-30 --workspace <workspace> --dataset-name <name>
```

**Post-verification:**
```bash
aliyun cms list-datasets --api-version 2024-03-30 --workspace <workspace> --dataset-name <name>
```
- Confirm the dataset no longer appears in the list

## 6. Execute Query

**Pre-check:**
```bash
aliyun cms get-dataset --api-version 2024-03-30 --workspace <workspace> --dataset-name <name>
```
- Confirm the dataset exists and inspect schema for valid field names

**Command:**
```bash
aliyun cms execute-query --api-version 2024-03-30 --workspace <workspace> \
  --dataset-name <name> --type SQL --query '<query>'
```

**Success criteria:**
- HTTP 200 response
- Response contains `requestId`, `meta`, and `data`
- `meta.progress` indicates query completion status

**Verification:**
- Check `meta.affectedRows` and `meta.count` for expected row counts
- Check `meta.elapsedMillisecond` for reasonable execution time
- Verify `data` contains the expected result structure
