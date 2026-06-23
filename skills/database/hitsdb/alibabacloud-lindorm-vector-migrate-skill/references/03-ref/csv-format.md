# CSV File Format Specification

Shared format definition for CSV import (`csv-import.md`) and export (`csv-export.md`).

## Header Row Format

`column_name:type`, all columns MUST declare their type.

```
id:long,title:text,price:float,embedding:knn_vector:128:cosine
1,Product A,99.9,"[0.1, 0.2, 0.3, 0.4]"
2,Product B,199.0,"[0.5, 0.6, 0.7, 0.8]"
```

## Type Identifiers

| Identifier | Description |
|------------|-------------|
| `long` | 64-bit integer |
| `integer` | 32-bit integer |
| `float` | Single-precision floating point |
| `double` | Double-precision floating point |
| `boolean` | Boolean value |
| `keyword` | Short string, not tokenized |
| `text` | Long text, tokenized |
| `date` | Date, ISO 8601 or `yyyy-MM-dd HH:mm:ss` |
| `knn_vector:dimension:distance_metric` | Vector column; distance metric options: `cosine` (default) / `l2` / `innerproduct` |

## Format Rules

- Type identifiers are case-insensitive
- `knn_vector` MUST specify dimension; distance metric can be omitted (defaults to cosine)
- Vector column values are JSON array strings; must be double-quoted if containing commas
- File encoding: UTF-8
- Delimiter: comma (,)
- Each row's column count must match the header

## Header Parsing

```python
def parse_header(fieldnames):
    """
    Input: ['id:long', 'title:text', 'embedding:knn_vector:128:cosine']
    Output:
      clean_names: ['id', 'title', 'embedding']
      schema: {'id': 'long', 'title': 'text', 'embedding': {'type': 'knn_vector', 'dim': 128, 'space': 'cosine'}}
    Raises: ValueError if a column is missing type declaration, column name is duplicated, or dimension is not an integer
    """
    clean_names = []
    schema = {}
    for field in fieldnames:
        parts = field.split(':')
        col_name = parts[0]
        if col_name in schema:
            raise ValueError(f"Column name '{col_name}' is duplicated")
        clean_names.append(col_name)
        if len(parts) == 1:
            raise ValueError(f"Column '{col_name}' is missing type declaration, format: column_name:type, e.g. {col_name}:keyword")
        elif parts[1].lower() == 'knn_vector':
            if len(parts) < 3:
                raise ValueError(f"Vector column '{col_name}' is missing dimension, correct format: {col_name}:knn_vector:128")
            try:
                dim = int(parts[2])
            except ValueError:
                raise ValueError(f"Vector column '{col_name}' dimension '{parts[2]}' is not a valid integer")
            space = parts[3].lower() if len(parts) > 3 else 'cosine'
            schema[col_name] = {'type': 'knn_vector', 'dim': dim, 'space': space}
        else:
            schema[col_name] = parts[1].lower()
    return clean_names, schema
```

## Vector Field Serialization

**Export** (list → string): `json.dumps(vec)` → `"[0.1, 0.2, 0.3]"`

**Import** (string → list):
```python
import json

def parse_vector(val, col, row_num):
    try:
        vec = json.loads(val)
        if not isinstance(vec, list) or not all(isinstance(x, (int, float)) for x in vec):
            raise ValueError
        return vec
    except (json.JSONDecodeError, ValueError):
        raise ValueError(f"Column '{col}' row {row_num} vector format error: '{val}'")
```
