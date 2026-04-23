# maxframe.dataframe.Series.nunique

#### Series.nunique(dropna=True)

Return number of unique elements in the object.

Excludes NA values by default.

* **Parameters:**
  **dropna** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Don’t include NaN in the count.
* **Return type:**
  [int](https://docs.python.org/3/library/functions.html#int)

#### SEE ALSO
[`DataFrame.nunique`](maxframe.dataframe.DataFrame.nunique.md#maxframe.dataframe.DataFrame.nunique)
: Method nunique for DataFrame.

[`Series.count`](maxframe.dataframe.Series.count.md#maxframe.dataframe.Series.count)
: Count non-NA/null observations in the Series.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series([1, 3, 5, 7, 7])
>>> s.execute()
0    1
1    3
2    5
3    7
4    7
dtype: int64
```

```pycon
>>> s.nunique().execute()
4
```
