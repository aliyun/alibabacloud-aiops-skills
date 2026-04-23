# maxframe.dataframe.DataFrame.last_valid_index

#### DataFrame.last_valid_index()

Return index for last non-NA value or None, if no non-NA value is found.

* **Return type:**
  [type](https://docs.python.org/3/library/functions.html#type) of index

### Examples

For Series:

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series([None, 3, 4])
>>> s.first_valid_index().execute()
1
>>> s.last_valid_index().execute()
2
```

```pycon
>>> s = md.Series([None, None])
>>> print(s.first_valid_index()).execute()
None
>>> print(s.last_valid_index()).execute()
None
```

If all elements in Series are NA/null, returns None.

```pycon
>>> s = md.Series()
>>> print(s.first_valid_index()).execute()
None
>>> print(s.last_valid_index()).execute()
None
```

If Series is empty, returns None.

For DataFrame:

```pycon
>>> df = md.DataFrame({'A': [None, None, 2], 'B': [None, 3, 4]})
>>> df.execute()
     A      B
0  NaN    NaN
1  NaN    3.0
2  2.0    4.0
>>> df.first_valid_index().execute()
1
>>> df.last_valid_index().execute()
2
```

```pycon
>>> df = md.DataFrame({'A': [None, None, None], 'B': [None, None, None]})
>>> df.execute()
     A      B
0  None   None
1  None   None
2  None   None
>>> print(df.first_valid_index()).execute()
None
>>> print(df.last_valid_index()).execute()
None
```

If all elements in DataFrame are NA/null, returns None.

```pycon
>>> df = md.DataFrame()
>>> df.execute()
Empty DataFrame
Columns: []
Index: []
>>> print(df.first_valid_index()).execute()
None
>>> print(df.last_valid_index()).execute()
None
```

If DataFrame is empty, returns None.
