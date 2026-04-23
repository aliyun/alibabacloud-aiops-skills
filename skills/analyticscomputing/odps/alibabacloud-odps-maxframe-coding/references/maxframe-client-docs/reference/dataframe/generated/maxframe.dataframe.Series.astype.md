# maxframe.dataframe.Series.astype

#### Series.astype(dtype, copy=True, errors='raise')

Cast a pandas object to a specified dtype `dtype`.

* **Parameters:**
  * **dtype** (*data type* *, or* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *of* *column name -> data type*) – Use a numpy.dtype or Python type to cast entire pandas object to
    the same type. Alternatively, use {col: dtype, …}, where col is a
    column label and dtype is a numpy.dtype or Python type to cast one
    or more of the DataFrame’s columns to column-specific types.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Return a copy when `copy=True` (be very careful setting
    `copy=False` as changes to values then may propagate to other
    pandas objects).
  * **errors** ( *{'raise'* *,*  *'ignore'}* *,* *default 'raise'*) – 

    Control raising of exceptions on invalid data for provided dtype.
    - `raise` : allow exceptions to be raised
    - `ignore` : suppress exceptions. On error return original object.
* **Returns:**
  **casted**
* **Return type:**
  same type as caller

#### SEE ALSO
[`to_datetime`](maxframe.dataframe.to_datetime.md#maxframe.dataframe.to_datetime)
: Convert argument to datetime.

`to_timedelta`
: Convert argument to timedelta.

[`to_numeric`](maxframe.dataframe.to_numeric.md#maxframe.dataframe.to_numeric)
: Convert argument to a numeric type.

[`numpy.ndarray.astype`](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.astype.html#numpy.ndarray.astype)
: Cast a numpy array to a specified type.

### Examples

Create a DataFrame:

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame(pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]}))
>>> df.dtypes
col1    int64
col2    int64
dtype: object
```

Cast all columns to int32:

```pycon
>>> df.astype('int32').dtypes
col1    int32
col2    int32
dtype: object
```

Cast col1 to int32 using a dictionary:

```pycon
>>> df.astype({'col1': 'int32'}).dtypes
col1    int32
col2    int64
dtype: object
```

Create a series:

```pycon
>>> ser = md.Series(pd.Series([1, 2], dtype='int32'))
>>> ser.execute()
0    1
1    2
dtype: int32
>>> ser.astype('int64').execute()
0    1
1    2
dtype: int64
```

Convert to categorical type:

```pycon
>>> ser.astype('category').execute()
0    1
1    2
dtype: category
Categories (2, int64): [1, 2]
```

Convert to ordered categorical type with custom ordering:

```pycon
>>> cat_dtype = pd.api.types.CategoricalDtype(
...     categories=[2, 1], ordered=True)
>>> ser.astype(cat_dtype).execute()
0    1
1    2
dtype: category
Categories (2, int64): [2 < 1]
```

Note that using `copy=False` and changing data on a new
pandas object may propagate changes:

```pycon
>>> s1 = md.Series(pd.Series([1, 2]))
>>> s2 = s1.astype('int64', copy=False)
>>> s1.execute()  # note that s1[0] has changed too
0     1
1     2
dtype: int64
```
