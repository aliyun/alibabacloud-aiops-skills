# maxframe.dataframe.get_dummies

### maxframe.dataframe.get_dummies(data, prefix=None, prefix_sep='_', dummy_na=False, columns=None, sparse=False, drop_first=False, dtype=None)

Convert categorical variable into dummy/indicator variables.

* **Parameters:**
  * **data** (*array-like* *,* [*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *, or* [*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)) – Data of which to get dummy indicators.
  * **prefix** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *, or* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *of* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – String to append DataFrame column names.
    Pass a list with length equal to the number of columns
    when calling get_dummies on a DataFrame. Alternatively, prefix
    can be a dictionary mapping column names to prefixes.
  * **prefix_sep** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default '_'*) – If appending prefix, separator/delimiter to use. Or pass a
    list or dictionary as with prefix.
  * **dummy_na** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Add a column to indicate NaNs, if False NaNs are ignored.
  * **columns** (*list-like* *,* *default None*) – Column names in the DataFrame to be encoded.
    If columns is None then all the columns with
    object or category dtype will be converted.
  * **sparse** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether the dummy-encoded columns should be backed by
    a `SparseArray` (True) or a regular NumPy array (False).
  * **drop_first** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether to get k-1 dummies out of k categorical levels by removing the
    first level.
  * **dtype** (*dtype* *,* *default bool*) – Data type for new columns. Only a single dtype is allowed.
* **Returns:**
  Dummy-coded data.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(list('abca'))
```

```pycon
>>> md.get_dummies(s).execute()
   a  b  c
0  1  0  0
1  0  1  0
2  0  0  1
3  1  0  0
```

```pycon
>>> s1 = ['a', 'b', np.nan]
```

```pycon
>>> md.get_dummies(s1).execute()
   a  b
0  1  0
1  0  1
2  0  0
```

```pycon
>>> md.get_dummies(s1, dummy_na=True).execute()
   a  b  NaN
0  1  0    0
1  0  1    0
2  0  0    1
```

```pycon
>>> df = md.DataFrame({'A': ['a', 'b', 'a'], 'B': ['b', 'a', 'c'],
...                    'C': [1, 2, 3]})
```

```pycon
>>> md.get_dummies(df, prefix=['col1', 'col2']).execute()
   C  col1_a  col1_b  col2_a  col2_b  col2_c
0  1       1       0       0       1       0
1  2       0       1       1       0       0
2  3       1       0       0       0       1
```

```pycon
>>> md.get_dummies(pd.Series(list('abcaa'))).execute()
   a  b  c
0  1  0  0
1  0  1  0
2  0  0  1
3  1  0  0
4  1  0  0
```

```pycon
>>> md.get_dummies(pd.Series(list('abcaa')), drop_first=True).execute()
   b  c
0  0  0
1  1  0
2  0  1
3  0  0
4  0  0
```

```pycon
>>> md.get_dummies(pd.Series(list('abc')), dtype=float).execute()
     a    b    c
0  1.0  0.0  0.0
1  0.0  1.0  0.0
2  0.0  0.0  1.0
```
