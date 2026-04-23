# maxframe.dataframe.Series.struct.field

#### Series.struct.field(name_or_index)

Extract a child field of a struct as a Series.

* **Parameters:**
  **name_or_index** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *|* [*bytes*](https://docs.python.org/3/library/stdtypes.html#bytes) *|* [*int*](https://docs.python.org/3/library/functions.html#int) *|* *expression* *|* [*list*](https://docs.python.org/3/library/stdtypes.html#list)) – 

  Name or index of the child field to extract.

  For list-like inputs, this will index into a nested
  struct.
* **Returns:**
  The data corresponding to the selected child field.
* **Return type:**
  [pandas.Series](https://pandas.pydata.org/docs/reference/api/pandas.Series.html#pandas.Series)

#### SEE ALSO
`Series.struct.explode`
: Return all child fields as a DataFrame.

### Notes

The name of the resulting Series will be set using the following
rules:

- For string, bytes, or integer name_or_index (or a list of these, for
  a nested selection), the Series name is set to the selected
  field’s name.
- For a `pyarrow.compute.Expression`, this is set to
  the string form of the expression.
- For list-like name_or_index, the name will be set to the
  name of the final field selected.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> import pandas as pd
>>> import pyarrow as pa
>>> s = md.Series(
...     [
...         {"version": 1, "project": "pandas"},
...         {"version": 2, "project": "pandas"},
...         {"version": 1, "project": "numpy"},
...     ],
...     dtype=pd.ArrowDtype(pa.struct(
...         [("version", pa.int64()), ("project", pa.string())]
...     ))
... )
```

Extract by field name.

```pycon
>>> s.struct.field("project").execute()
0    pandas
1    pandas
2     numpy
Name: project, dtype: string[pyarrow]
```

Extract by field index.

```pycon
>>> s.struct.field(0).execute()
0    1
1    2
2    1
Name: version, dtype: int64[pyarrow]
```

For nested struct types, you can pass a list of values to index
multiple levels:

```pycon
>>> version_type = pa.struct([
...     ("major", pa.int64()),
...     ("minor", pa.int64()),
... ])
>>> s = md.Series(
...     [
...         {"version": {"major": 1, "minor": 5}, "project": "pandas"},
...         {"version": {"major": 2, "minor": 1}, "project": "pandas"},
...         {"version": {"major": 1, "minor": 26}, "project": "numpy"},
...     ],
...     dtype=pd.ArrowDtype(pa.struct(
...         [("version", version_type), ("project", pa.string())]
...     ))
... )
>>> s.struct.field(["version", "minor"]).execute()
0     5
1     1
2    26
Name: minor, dtype: int64[pyarrow]
>>> s.struct.field([0, 0]).execute()
0    1
1    2
2    1
Name: major, dtype: int64[pyarrow]
```
