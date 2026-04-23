# maxframe.dataframe.Series.add_prefix

#### Series.add_prefix(prefix)

Prefix labels with string prefix.

For Series, the row labels are prefixed.
For DataFrame, the column labels are prefixed.

* **Parameters:**
  **prefix** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The string to add before each label.
* **Returns:**
  New Series or DataFrame with updated labels.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`Series.add_suffix`](maxframe.dataframe.Series.add_suffix.md#maxframe.dataframe.Series.add_suffix)
: Suffix row labels with string suffix.

[`DataFrame.add_suffix`](maxframe.dataframe.DataFrame.add_suffix.md#maxframe.dataframe.DataFrame.add_suffix)
: Suffix column labels with string suffix.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series([1, 2, 3, 4])
>>> s.execute()
0    1
1    2
2    3
3    4
dtype: int64
```

```pycon
>>> s.add_prefix('item_').execute()
item_0    1
item_1    2
item_2    3
item_3    4
dtype: int64
```

```pycon
>>> df = md.DataFrame({'A': [1, 2, 3, 4], 'B': [3, 4, 5, 6]})
>>> df.execute()
   A  B
0  1  3
1  2  4
2  3  5
3  4  6
```

```pycon
>>> df.add_prefix('col_').execute()
     col_A  col_B
0        1      3
1        2      4
2        3      5
3        4      6
```
