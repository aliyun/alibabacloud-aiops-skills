# maxframe.dataframe.to_numeric

### maxframe.dataframe.to_numeric(arg, errors='raise', downcast=None)

Convert argument to a numeric type.

The default return dtype is float64 or int64
depending on the data supplied. Use the downcast parameter
to obtain other dtypes.

Please note that precision loss may occur if really large numbers
are passed in. Due to the internal limitations of ndarray, if
numbers smaller than -9223372036854775808 (np.iinfo(np.int64).min)
or larger than 18446744073709551615 (np.iinfo(np.uint64).max) are
passed in, it is very likely they will be converted to float so that
they can stored in an ndarray. These warnings apply similarly to
Series since it internally leverages ndarray.

* **Parameters:**
  * **arg** (*scalar* *,* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *,* *1-d array* *, or* [*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – Argument to be converted.
  * **errors** ( *{'ignore'* *,*  *'raise'* *,*  *'coerce'}* *,* *default 'raise'*) – 
    - If ‘raise’, then invalid parsing will raise an exception.
    - If ‘coerce’, then invalid parsing will be set as NaN.
    - If ‘ignore’, then invalid parsing will return the input.
  * **downcast** ( *{'integer'* *,*  *'signed'* *,*  *'unsigned'* *,*  *'float'}* *,* *default None*) – 

    If not None, and if the data has been successfully cast to a
    numerical dtype (or if the data was numeric to begin with),
    downcast that resulting data to the smallest numerical dtype
    possible according to the following rules:
    - ’integer’ or ‘signed’: smallest signed int dtype (min.: np.int8)
    - ’unsigned’: smallest unsigned int dtype (min.: np.uint8)
    - ’float’: smallest float dtype (min.: np.float32)

    As this behaviour is separate from the core conversion to
    numeric values, any errors raised during the downcasting
    will be surfaced regardless of the value of the ‘errors’ input.

    In addition, downcasting will only occur if the size
    of the resulting data’s dtype is strictly larger than
    the dtype it is to be cast to, so if none of the dtypes
    checked satisfy that specification, no downcasting will be
    performed on the data.
* **Returns:**
  Numeric if parsing succeeded.
  Return type depends on input.  Series if Series, otherwise Tensor.
* **Return type:**
  ret

#### SEE ALSO
[`DataFrame.astype`](maxframe.dataframe.DataFrame.astype.md#maxframe.dataframe.DataFrame.astype)
: Cast argument to a specified dtype.

[`to_datetime`](maxframe.dataframe.to_datetime.md#maxframe.dataframe.to_datetime)
: Convert argument to datetime.

`to_timedelta`
: Convert argument to timedelta.

[`numpy.ndarray.astype`](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.astype.html#numpy.ndarray.astype)
: Cast a numpy array to a specified type.

[`DataFrame.convert_dtypes`](maxframe.dataframe.DataFrame.convert_dtypes.md#maxframe.dataframe.DataFrame.convert_dtypes)
: Convert dtypes.

### Examples

Take separate series and convert to numeric, coercing when told to

```pycon
>>> s = md.Series(['1.0', '2', -3])
>>> md.to_numeric(s).execute()
0    1.0
1    2.0
2   -3.0
dtype: float64
>>> md.to_numeric(s, downcast='float').execute()
0    1.0
1    2.0
2   -3.0
dtype: float32
>>> md.to_numeric(s, downcast='signed').execute()
0    1
1    2
2   -3
dtype: int8
>>> s = md.Series(['apple', '1.0', '2', -3])
>>> md.to_numeric(s, errors='ignore').execute()
0    apple
1      1.0
2        2
3       -3
dtype: object
>>> md.to_numeric(s, errors='coerce').execute()
0    NaN
1    1.0
2    2.0
3   -3.0
dtype: float64
```

Downcasting of nullable integer and floating dtypes is supported:

```pycon
>>> s = md.Series([1, 2, 3], dtype="int64")
>>> md.to_numeric(s, downcast="integer").execute()
0    1
1    2
2    3
dtype: int8
>>> s = md.Series([1.0, 2.1, 3.0], dtype="float64")
>>> md.to_numeric(s, downcast="float").execute()
0    1.0
1    2.1
2    3.0
dtype: float32
```
