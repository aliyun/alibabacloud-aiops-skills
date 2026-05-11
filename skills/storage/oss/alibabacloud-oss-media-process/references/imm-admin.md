# IMM Administration

Use `scripts/imm_admin.py` to manage IMM (Intelligent Media Management) projects and bucket bindings. IMM projects are required for image-intelligent operations such as blind watermark extraction and AI detection.

IMM administration requires specific RAM permissions (imm:CreateProject, imm:GetProject, imm:ListProjects, imm:DeleteProject, imm:AttachOSSBucket, imm:DetachOSSBucket).

## Commands

### Create an IMM project

```bash
python scripts/imm_admin.py create-project --project PROJECT_NAME --region REGION_ID
```

### List all projects

```bash
python scripts/imm_admin.py list-projects --region REGION_ID
```

### Get project details

```bash
python scripts/imm_admin.py get-project --project PROJECT_NAME --region REGION_ID
```

### Bind a bucket to a project

```bash
python scripts/imm_admin.py bind-bucket --project PROJECT_NAME --bucket BUCKET_NAME --region REGION_ID
```

### Unbind a bucket from a project

```bash
python scripts/imm_admin.py unbind-bucket --project PROJECT_NAME --bucket BUCKET_NAME --region REGION_ID
```

### Delete a project

```bash
python scripts/imm_admin.py delete-project --project PROJECT_NAME --region REGION_ID
```

The delete command includes a protective pre-check: it queries the project's dataset count and blocks deletion if any datasets (bound buckets) remain. Unbind all buckets before deleting.

## Typical Setup Flow

```bash
# 1. Create an IMM project
python scripts/imm_admin.py create-project --project my-imm-project --region cn-hangzhou

# 2. Bind your OSS bucket to the project
python scripts/imm_admin.py bind-bucket --project my-imm-project --bucket my-bucket --region cn-hangzhou

# 3. Verify the setup
python scripts/imm_admin.py get-project --project my-imm-project --region cn-hangzhou
```

After setup, you can use IMM operations in `scripts/process.py` with `--imm-project my-imm-project`.
