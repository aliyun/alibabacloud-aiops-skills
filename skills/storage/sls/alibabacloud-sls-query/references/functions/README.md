# SLS Function Reference

This directory contains all functions supported by SLS SQL and SPL analysis statements, organized by category.

## Directory Structure

| File | Category | Description | Supported In |
|------|----------|-------------|--------------|
| `aggregate.yaml` | Aggregate Functions | count, sum, avg, max, min and other statistical functions | SQL |
| `string.yaml` | String Functions | Text concatenation, substring, case conversion, find & replace | SQL + SPL |
| `regex.yaml` | Regex Functions | Regex match, extract, replace | SQL + SPL |
| `datetime.yaml` | Date/Time Functions | Time formatting, parsing, truncation, conversion | SQL + SPL |
| `type_conversion.yaml` | Type Conversion Functions | cast, try_cast type conversion | SQL + SPL |
| `conditional.yaml` | Conditional Functions | if, case, coalesce conditional logic | SQL + SPL |
| `json.yaml` | JSON Functions | JSON data extraction and parsing | SQL + SPL |
| `math.yaml` | Math Functions | Numeric calculations, rounding, exponentiation | SQL + SPL |
| `url.yaml` | URL Functions | URL parsing and parameter extraction | SQL + SPL |
| `ip_geo.yaml` | IP Geolocation Functions | IP to province, city, country, coordinates | SPL only |
| `encoding.yaml` | Encoding/Decoding Functions | URL, Base64 encoding and decoding | SQL + SPL |
| `hash.yaml` | Hash Functions | MD5, SHA1, SHA256 hash computation | SQL + SPL |

## Usage

### 1. Finding Functions

- **By category**: Select the corresponding file from the table above
- **By name**: Search for the specific function in the relevant YAML file
- **By scenario**: Refer to `overview.yaml` for common scenario examples

### 2. Function Details

Each YAML file contains the following structure:

```yaml
functions:
  - name: function_name
    syntax: function_syntax
    description: what_it_does
    examples:
      sql: SQL example
      spl: SPL example
    note: caveats (optional)
```

### 3. Important Notes

#### Type Conversion
- Fields default to VARCHAR type
- Always use `cast()` or `try_cast()` before numeric comparison or arithmetic
- Pay special attention to type conversion in SPL

Example:
```sql
-- Correct
* | SELECT * WHERE cast(status as BIGINT) >= 500

-- Wrong
* | SELECT * WHERE status >= 500
```

#### SQL vs SPL
- **SQL**: uses SELECT, WHERE, GROUP BY syntax
- **SPL**: uses extend, where, stats syntax
- **Aggregate functions** are primarily used in SQL
- **IP geo functions** are SPL only

#### Regular Expressions
- SPL uses the RE2 regex engine
- Not supported: back-references (\1), lookaround (?<=...), etc.
- No double-escaping needed: `\d` is written as `\d`

## Quick Examples

### Statistical Analysis
```sql
-- Count by status code
* | SELECT status, count(*) AS pv GROUP BY status ORDER BY pv DESC
```

### Time Grouping
```sql
-- Hourly aggregation
* | SELECT date_trunc('hour', __time__) AS hour, count(*) AS pv GROUP BY hour
```

### Regex Extraction
```sql
-- Extract error codes
* | SELECT regexp_extract(message, 'code:(\d+)', 1) AS error_code, count(*) GROUP BY error_code
```

### JSON Parsing
```sql
-- Extract JSON fields
* | SELECT json_extract_scalar(payload, '$.user.name') AS user, count(*) GROUP BY user
```

### IP Geo Analysis (SPL)
```spl
# Count by province
* | extend province = ip_to_province(client_ip) | stats pv = count(*) by province
```

## Related Documents

- [Function Index](./overview.yaml) - Function category index and usage guide
- [SQL Query Syntax](../query_analysis/sql.yaml) - Complete SQL query syntax
- [SPL Basic Syntax](../spl/overview.yaml) - SPL query basics
- [Index Search](../query_analysis/indexSearch.yaml) - Keyword search syntax
