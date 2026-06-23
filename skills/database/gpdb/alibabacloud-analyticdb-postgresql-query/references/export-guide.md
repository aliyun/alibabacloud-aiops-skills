# Export Guide

## Exporting Query Results to CSV

### Standard Method (Recommended)

```bash
# \copy export (with header)
psql -c "\copy (SELECT id, name, value FROM my_table WHERE status='active') TO 'result.csv' CSV HEADER"
```

### Other Formats

```bash
# Without header
psql -c "\copy (SELECT ...) TO 'result.csv' CSV"

# Custom delimiter (e.g., TSV)
psql -c "\copy (SELECT ...) TO 'result.tsv' DELIMITER E'\t' CSV HEADER"

# Direct CSV output to stdout (can be piped)
psql --csv -c "SELECT ..."
```

---

## Post-Export Verification

```bash
wc -l result.csv        # Line count (including header)
head -3 result.csv      # Preview first few lines
ls -lh result.csv       # File size
```

---

## Large Data Export Strategy

- **Confirm volume first**: `psql -c "SELECT COUNT(*) FROM ..."`
- **Batch export**: Shard by date range or ID range
- **Limit rows**: Add `LIMIT` in SQL; export to multiple files as needed

```bash
# Batch example
psql -c "\copy (SELECT * FROM logs WHERE dt='2024-01-01') TO 'logs_0101.csv' CSV HEADER"
psql -c "\copy (SELECT * FROM logs WHERE dt='2024-01-02') TO 'logs_0102.csv' CSV HEADER"
```

---

## Local Analysis Integration

After the CSV is saved, the Agent can read it directly for further analysis:

```python
import pandas as pd

df = pd.read_csv("result.csv")
print(df.shape)          # Row and column count
print(df.describe())     # Basic statistics
print(df.head())         # Preview

# Multi-file join
df2 = pd.read_csv("other.csv")
merged = df.merge(df2, on="id")
```

You can also use shell commands for quick processing:

```bash
# Count lines
wc -l result.csv

# Sort by a column
sort -t',' -k3 -n result.csv | tail -10

# Deduplicate
sort -u result.csv > dedup.csv
```
