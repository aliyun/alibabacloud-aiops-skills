# maxframe.dataframe.Series.struct.dtypes

#### Series.struct.dtypes()

Return the dtype object of each child field of the struct.

* **Returns:**
  The data type of each child field.
* **Return type:**
  [pandas.Series](https://pandas.pydata.org/docs/reference/api/pandas.Series.html#pandas.Series)

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
>>> s.struct.dtypes.execute()
version     int64[pyarrow]
project    string[pyarrow]
dtype: object
```
