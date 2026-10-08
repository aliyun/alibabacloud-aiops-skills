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

Batch-first applies only when the task fits batch semantics. When it does not (one row expands to many, whole groups needed at once, two tables must be paired), choose the UDF operator by data shape instead — see Rule 5.

### 3. Pandas Compatibility First

MaxFrame provides pandas-compatible APIs. When multiple options exist, prefer pandas-compatible operators that users are already familiar with.

### 4. Provide Alternatives

When recommending operators, always provide fallback options:
- Primary recommendation (best engine support, best performance)
- Alternative 1 (if primary has limitations or partial support)
- Alternative 2 (if primary is not supported on current engine)
- UDF approach (if no native operator is available)

### 5. UDF Operator Selection by Scenario

When no native operator fits, recommend a UDF operator by **data shape**, not by a flat performance ranking. UDF operators differ in what the function receives (scalar / row / chunk / whole group / chunk pairs) and in how row counts change (1→1, N→M, 1→0..N). Pick the operator whose semantics match the task first; use performance only to break ties between operators with the same semantics.

#### Step 1: Classify Data Organization

- **Single table** — one input DataFrame/Series
- **Grouped** — logic runs per group (`groupby` keys)
- **Two tables** — logic pairs or compares rows from two DataFrames

#### Step 2: Match Row Cardinality and Semantics

| Branch | Task shape | Recommended operator | Key notes |
|--------|-----------|----------------------|-----------|
| Single | Element-wise 1→1 (value → value) | `Series.map` / `DataFrame.map` | Dict lookup via `Series.map(dict)` is native, not a UDF |
| Single | Row-wise scalar (1 row → 1 value) | `DataFrame.apply(func, axis=1)` | Avoid `Series.apply` (generates a join, see below) |
| Single | Batch N→M: vectorizable logic, batch inference, amortized per-call init | `DataFrame.mf.apply_chunk(func, batch_rows=)` | func receives a pandas DataFrame of ≤ `batch_rows`; if type inference fails, specify `output_type` + `dtypes`/`dtype` |
| Single | One row → 0..N rows (explode / generate) | `DataFrame.mf.flatmap(func, dtypes=)` | func returns an iterable per row; `dtypes` is REQUIRED — flatmap has no type inference |
| Grouped | Output keeps input shape | `GroupBy.transform(func)` | like-indexed result |
| Grouped | Custom aggregation: map rows, then aggregate by key | `DataFrame.mf.map_reduce(mapper, reducer, group_cols=)` | Shortcut for `apply_chunk(mapper).groupby(group_cols).mf.apply_chunk(reducer)`; add `combiner` to pre-aggregate mapper output and cut shuffle on high-cardinality keys; reducer may be a class with `__call__(batch, end=False)` + `close()` |
| Grouped | Batch processing inside large groups, in-group ordering | `GroupBy.mf.apply_chunk(func, batch_rows=, order_cols=)` | A group may be split into multiple batches; do not assume the whole group arrives in one call |
| Grouped | Whole group needed in one call | `GroupBy.apply(func)` | Most flexible, slowest; last resort |
| Two tables | Pairwise comparison / custom join logic | `DataFrame.mf.cartesian_chunk(other, func)` | func receives one chunk from each side and runs on EVERY chunk pair (cartesian); if inference fails, `output_type` + `dtypes` are required. Not covered by `lookup_operator.py` — see `references/practical-guides/udf-development-guide.md` |

#### Performance Tie-breakers (Same Semantics Only)

- When a task can be expressed both row-wise (`DataFrame.apply`) and batch-wise (`mf.apply_chunk`), prefer batch-wise on large data.
- Prefer vectorized pandas/numpy inside the UDF over Python row loops.
- Size CPU/memory/GU to batch size with `with_running_options` (see `key-modules.md`).

After selecting the operator, retrieve its signature and examples before writing code: `python scripts/lookup_operator.py info <operator> -s signature` and `-s examples`.

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
4. **Prepare alternative options** with different operators or UDF approaches — UDF alternatives must come from the same branch of the Rule 5 scenario table (same data shape), never from a different cardinality family (e.g., do not offer `apply_chunk` as the fallback for a one-row-to-many task)
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
- **Include UDF fallback** - provide custom function approach when native operators are unavailable, selected via the Rule 5 scenario table
- **Use section extraction** to avoid loading large documentation files
- **Reference actual documentation** for accurate information

## Reference

For complete API documentation:
- See `maxframe-client-docs/` directory
- See `supported_pd_apis.md` for engine support matrix
- Use `lookup_operator.py` script for detailed operator information
