# Success Verification Method

## Scenario Goal Verification

**Expected Outcome**: Able to successfully query Catalog, database, and table metadata in the DLF data lake.

### Step 1: Verify SDK installation

```bash
python3 -c "from alibabacloud_dlfnext20250310.client import Client; print('SDK OK')"
```

**Success Indicator**: outputs `SDK OK`.

### Step 2: Verify credential configuration

```bash
python3 -c "from alibabacloud_credentials.client import Client; Client(); print('Credentials OK')"
```

**Success Indicator**: outputs `Credentials OK` (the default credential chain finds valid credentials).

### Step 3: Verify Catalog list query

```bash
python3 scripts/dlf_metadata_query.py list-catalogs --region cn-hangzhou
```

**Success Indicator**: returns the Catalog list in JSON format with `count` and `items` fields.

### Step 4: Verify the end-to-end query chain

```bash
# 1. List Catalogs and get catalog_id
python3 scripts/dlf_metadata_query.py list-catalogs

# 2. Use catalog_id to list databases
python3 scripts/dlf_metadata_query.py list-databases --catalog-id <catalog_id>

# 3. Use catalog_id + database to list tables
python3 scripts/dlf_metadata_query.py list-tables --catalog-id <catalog_id> --database <db_name>

# 4. Use catalog_id + database + table to view the table Schema
python3 scripts/dlf_metadata_query.py get-table --catalog-id <catalog_id> --database <db_name> --table <table_name>
```

**Success Indicator**: every step returns valid JSON; the final get-table returns the complete table structure including `schema.fields`.

### Common Failure Causes

| Error message | Cause | Resolution |
|---------|------|---------|
| `No credentials found` | Environment variables not configured | Set AK/SK environment variables |
| `Permission denied` | Missing DLF data permissions | Grant access in the DLF console |
| `Resource not found` | Wrong Catalog/DB/Table name | Verify the resource names |
| `SDK not installed` | Python SDK not installed | `pip install alibabacloud-dlfnext20250310` |
