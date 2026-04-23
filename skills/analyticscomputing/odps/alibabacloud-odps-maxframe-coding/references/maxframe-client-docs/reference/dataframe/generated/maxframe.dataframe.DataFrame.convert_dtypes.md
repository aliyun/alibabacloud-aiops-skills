# maxframe.dataframe.DataFrame.convert_dtypes

#### DataFrame.convert_dtypes(infer_objects=True, convert_string=True, convert_integer=True, convert_boolean=True, convert_floating=True, dtype_backend='numpy')

Convert columns to best possible dtypes using dtypes supporting `pd.NA`.

* **Parameters:**
  * **infer_objects** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Whether object dtypes should be converted to the best possible types.
  * **convert_string** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Whether object dtypes should be converted to `StringDtype()`.
  * **convert_integer** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Whether, if possible, conversion can be done to integer extension types.
  * **convert_boolean** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *defaults True*) – Whether object dtypes should be converted to `BooleanDtypes()`.
  * **convert_floating** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *defaults True*) – Whether, if possible, conversion can be done to floating extension types.
    If convert_integer is also True, preference will be give to integer
    dtypes if the floats can be faithfully casted to integers.
* **Returns:**
  Copy of input object with new dtype.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`infer_objects`](maxframe.dataframe.DataFrame.infer_objects.md#maxframe.dataframe.DataFrame.infer_objects)
: Infer dtypes of objects.

[`to_datetime`](maxframe.dataframe.to_datetime.md#maxframe.dataframe.to_datetime)
: Convert argument to datetime.

`to_timedelta`
: Convert argument to timedelta.

[`to_numeric`](maxframe.dataframe.to_numeric.md#maxframe.dataframe.to_numeric)
: Convert argument to a numeric type.

### Notes

By default, `convert_dtypes` will attempt to convert a Series (or each
Series in a DataFrame) to dtypes that support `pd.NA`. By using the options
`convert_string`, `convert_integer`, `convert_boolean` and
`convert_boolean`, it is possible to turn off individual conversions
to `StringDtype`, the integer extension types, `BooleanDtype`
or floating extension types, respectively.

For object-dtyped columns, if `infer_objects` is `True`, use the inference
rules as during normal Series/DataFrame construction.  Then, if possible,
convert to `StringDtype`, `BooleanDtype` or an appropriate integer
or floating extension type, otherwise leave as `object`.

If the dtype is integer, convert to an appropriate integer extension type.

If the dtype is numeric, and consists of all integers, convert to an
appropriate integer extension type. Otherwise, convert to an
appropriate floating extension type.

#### Versionchanged
Changed in version 1.2: Starting with pandas 1.2, this method also converts float columns
to the nullable floating extension type.

In the future, as new dtypes are added that support `pd.NA`, the results
of this method will change to support those new dtypes.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame(
...     {
...         "a": md.Series([1, 2, 3], dtype=mt.dtype("int32")),
...         "b": md.Series(["x", "y", "z"], dtype=mt.dtype("O")),
...         "c": md.Series([True, False, mt.nan], dtype=mt.dtype("O")),
...         "d": md.Series(["h", "i", mt.nan], dtype=mt.dtype("O")),
...         "e": md.Series([10, mt.nan, 20], dtype=mt.dtype("float")),
...         "f": md.Series([mt.nan, 100.5, 200], dtype=mt.dtype("float")),
...     }
... )
```

Start with a DataFrame with default dtypes.

```pycon
>>> df.execute()
   a  b      c    d     e      f
0  1  x   True    h  10.0    NaN
1  2  y  False    i   NaN  100.5
2  3  z    NaN  NaN  20.0  200.0
```

```pycon
>>> df.dtypes.execute()
a      int32
b     object
c     object
d     object
e    float64
f    float64
dtype: object
```

Convert the DataFrame to use best possible dtypes.

```pycon
>>> dfn = df.convert_dtypes()
>>> dfn.execute()
   a  b      c     d     e      f
0  1  x   True     h    10   <NA>
1  2  y  False     i  <NA>  100.5
2  3  z   <NA>  <NA>    20  200.0
```

```pycon
>>> dfn.dtypes.execute()
a      Int32
b     string
c    boolean
d     string
e      Int64
f    Float64
dtype: object
```

Start with a Series of strings and missing data represented by `np.nan`.

```pycon
>>> s = md.Series(["a", "b", mt.nan])
>>> s.execute()
0      a
1      b
2    NaN
dtype: object
```

Obtain a Series with dtype `StringDtype`.

```pycon
>>> s.convert_dtypes().execute()
0       a
1       b
2    <NA>
dtype: string
```
