# Operator Selection Rules

This document provides guidance for selecting and recommending MaxFrame operators. The operator-selector agent uses the `lookup_operator.py` script to find, verify, and recommend operators based on actual MaxFrame documentation.

## Core Principles

### 1. Performance First

Prefer operators optimized for distributed execution:
- Use `.mf.apply_chunk()` for batch processing of large datasets
- Use vectorized operations instead of row-wise operations
- Use built-in aggregations instead of custom UDFs when possible

### 2. Batch First

For processing large datasets, prioritize batch operations:
- Use `.mf.apply_chunk()` for custom functions on large data
- Use `.mf.map_reduce()` for map-reduce patterns
- Process data in chunks to distribute workload

### 3. Pandas Compatibility First

MaxFrame provides pandas-compatible APIs. When multiple options exist, prefer pandas-compatible operators that users are already familiar with.

### 4. Provide Alternatives

When recommending operators, always provide fallback options:
- Primary recommendation (best engine support, best performance)
- Alternative 1 (if primary has limitations or partial support)
- Alternative 2 (if primary is not supported on current engine)
- UDF approach (if no native operator is available)

### 5. UDF Fallback for Unsupported Operators

When an operator is not supported or has significant limitations, provide a UDF-based solution:
- Use `.apply()` with a custom function
- Use `.mf.apply_chunk()` for distributed UDF execution
- Prefer `dataframe.mf.apply_chunk` than `dataframe.apply` than `series.apply`.
- Document any performance implications of the UDF approach

## Engine Support Priority

MaxFrame operators run on different execution engines. Check `./maxframe-client-docs/user_guide/dataframe/supported_pd_apis.md` for detailed support matrix.

**Priority order:**
1. **SQL Engine (MCSQL)** - Highest priority, best performance
2. **DPE** - Good performance, broader API support
3. **SPE** - Lowest priority, fallback option

When recommending an operator, check if it's supported on SQL Engine first. If not, check DPE, then SPE.

**Legend:**
- `Y` - Fully supported
- `P` - Partially supported (see Details column)
- `N` - Not supported

## Using lookup_operator.py

The `lookup_operator.py` script is the authoritative source for operator information. Always use it to verify operator existence, get signatures, and retrieve documentation.

### Available Commands

#### List All Operators

```bash
python scripts/lookup_operator.py list [--fold] [--json]
```

#### Search for Operators

```bash
python scripts/lookup_operator.py search <pattern> [-n|--name-only] [--fold] [--json]
```

#### Get Operator Information

```bash
python scripts/lookup_operator.py info <name> [-s|--section SECTION] [--json]
```

### Available Sections for Info Command

- `signature` - Function signature
- `description` - Description paragraphs
- `params` / `parameters` - Parameters section
- `returns` - Returns section
- `return_type` - Return type
- `see_also` - See Also section
- `notes` - Notes section
- `examples` - Examples section

Sections can be empty.

## Operator Selection Guidelines

### Check Series.apply Implications

`Series.apply()` currently generates a join operation which can be expensive. Prefer:
- `DataFrame.apply()` when working with DataFrames
- `DataFrame.mf.apply_chunk()` for batch processing on large datasets
- Vectorized operations when possible

## Workflow for Operator Selection

1. **Search** for operators matching the task description
2. **Validate** operator existence and engine support
3. **Check for known issues** (e.g., Series.apply generates joins)
4. **Prepare alternative options** with different operators or UDF approaches
5. **Retrieve** only the sections needed (signature, examples, etc.)
6. **Recommend** with primary choice and fallbacks

## Example

```bash
# Find operators for time series operations
python scripts/lookup_operator.py search rolling

# Get full info on a specific operator
python scripts/lookup_operator.py info DataFrame.rolling

# Get only the signature and examples
python scripts/lookup_operator.py info DataFrame.rolling -s signature
python scripts/lookup_operator.py info DataFrame.rolling -s examples

# Check if operator is supported on SQL Engine
grep "rolling" references/maxframe-client-docs/user_guide/dataframe/supported_pd_apis.md
```

## Important

- **Never assume** operator behavior - always use lookup_operator.py
- **Always verify** operator existence before recommending
- **Check engine support** in supported_pd_apis.md for compatibility
- **Provide alternatives** - always give backup options if primary has limitations
- **Include UDF fallback** - provide custom function approach when native operators are unavailable
- **Use section extraction** to avoid loading large documentation files
- **Reference actual documentation** for accurate information

## Reference

For complete API documentation:
- See `maxframe-client-docs/` directory
- See `supported_pd_apis.md` for engine support matrix
- Use `lookup_operator.py` script for detailed operator information
