# maxframe.dataframe.Series.infer_objects

#### Series.infer_objects(copy=True)

Attempt to infer better dtypes for object columns.

Attempts soft conversion of object-dtyped
columns, leaving non-object and unconvertible
columns unchanged. The inference rules are the
same as during normal Series/DataFrame construction.

* **Returns:**
  **converted**
* **Return type:**
  same type as input object

#### SEE ALSO
[`to_datetime`](maxframe.dataframe.to_datetime.md#maxframe.dataframe.to_datetime)
: Convert argument to datetime.

`to_timedelta`
: Convert argument to timedelta.

[`to_numeric`](maxframe.dataframe.to_numeric.md#maxframe.dataframe.to_numeric)
: Convert argument to numeric type.

[`convert_dtypes`](maxframe.dataframe.Series.convert_dtypes.md#maxframe.dataframe.Series.convert_dtypes)
: Convert argument to best possible dtype.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({"A": ["a", 1, 2, 3]})
>>> df = df.iloc[1:]
>>> df.execute()
   A
1  1
2  2
3  3
```

```pycon
>>> df.dtypes.execute()
A    object
dtype: object
```

```pycon
>>> df.infer_objects().dtypes.execute()
A    int64
dtype: object
```
