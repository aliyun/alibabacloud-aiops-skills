# maxframe.dataframe.DataFrame.select_dtypes

#### DataFrame.select_dtypes(include=None, exclude=None)

Return a subset of the DataFrame’s columns based on the column dtypes.

* **Parameters:**
  * **include** (*scalar* *or* *list-like*) – A selection of dtypes or strings to be included/excluded. At least
    one of these parameters must be supplied.
  * **exclude** (*scalar* *or* *list-like*) – A selection of dtypes or strings to be included/excluded. At least
    one of these parameters must be supplied.
* **Returns:**
  The subset of the frame including the dtypes in `include` and
  excluding the dtypes in `exclude`.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – 
  * If both of `include` and `exclude` are empty
        \* If `include` and `exclude` have overlapping elements
        \* If any kind of string dtype is passed in.

#### SEE ALSO
[`DataFrame.dtypes`](maxframe.dataframe.DataFrame.dtypes.md#maxframe.dataframe.DataFrame.dtypes)
: Return Series with the data type of each column.

### Notes

* To select all *numeric* types, use `np.number` or `'number'`
* To select strings you must use the `object` dtype, but note that
  this will return *all* object dtype columns
* See the [numpy dtype hierarchy](https://numpy.org/doc/stable/reference/arrays.scalars.html)
* To select datetimes, use `np.datetime64`, `'datetime'` or
  `'datetime64'`
* To select timedeltas, use `np.timedelta64`, `'timedelta'` or
  `'timedelta64'`
* To select Pandas categorical dtypes, use `'category'`
* To select Pandas datetimetz dtypes, use `'datetimetz'` (new in
  0.20.0) or `'datetime64[ns, tz]'`

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'a': [1, 2] * 3,
...                    'b': [True, False] * 3,
...                    'c': [1.0, 2.0] * 3})
>>> df.execute()
        a      b  c
0       1   True  1.0
1       2  False  2.0
2       1   True  1.0
3       2  False  2.0
4       1   True  1.0
5       2  False  2.0
```

```pycon
>>> df.select_dtypes(include='bool').execute()
   b
0  True
1  False
2  True
3  False
4  True
5  False
```

```pycon
>>> df.select_dtypes(include=['float64']).execute()
   c
0  1.0
1  2.0
2  1.0
3  2.0
4  1.0
5  2.0
```

```pycon
>>> df.select_dtypes(exclude=['int64']).execute()
       b    c
0   True  1.0
1  False  2.0
2   True  1.0
3  False  2.0
4   True  1.0
5  False  2.0
```
