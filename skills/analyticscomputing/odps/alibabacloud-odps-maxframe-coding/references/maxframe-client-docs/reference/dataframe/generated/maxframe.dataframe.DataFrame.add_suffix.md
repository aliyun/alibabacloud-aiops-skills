# maxframe.dataframe.DataFrame.add_suffix

#### DataFrame.add_suffix(suffix)

Suffix labels with string suffix.

For Series, the row labels are suffixed.
For DataFrame, the column labels are suffixed.

* **Parameters:**
  **suffix** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The string to add after each label.
* **Returns:**
  New Series or DataFrame with updated labels.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`Series.add_prefix`](maxframe.dataframe.Series.add_prefix.md#maxframe.dataframe.Series.add_prefix)
: Suffix row labels with string prefix.

[`DataFrame.add_prefix`](maxframe.dataframe.DataFrame.add_prefix.md#maxframe.dataframe.DataFrame.add_prefix)
: Suffix column labels with string prefix.

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
>>> s.add_prefix('_item').execute()
0_item    1
1_item    2
2_item    3
3_item    4
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
>>> df.add_prefix('_col').execute()
     A_col  B_col
0        1      3
1        2      4
2        3      5
3        4      6
```
