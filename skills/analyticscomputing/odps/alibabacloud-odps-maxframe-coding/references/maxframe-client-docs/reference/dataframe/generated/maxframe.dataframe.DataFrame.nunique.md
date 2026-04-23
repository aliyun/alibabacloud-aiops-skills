# maxframe.dataframe.DataFrame.nunique

#### DataFrame.nunique(axis=0, dropna=True)

Count distinct observations over requested axis.

Return Series with number of distinct observations. Can ignore NaN
values.

* **Parameters:**
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – The axis to use. 0 or ‘index’ for row-wise, 1 or ‘columns’ for
    column-wise.
  * **dropna** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Don’t include NaN in the counts.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Series.nunique`](maxframe.dataframe.Series.nunique.md#maxframe.dataframe.Series.nunique)
: Method nunique for Series.

[`DataFrame.count`](maxframe.dataframe.DataFrame.count.md#maxframe.dataframe.DataFrame.count)
: Count non-NA cells for each column or row.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'A': [1, 2, 3], 'B': [1, 1, 1]})
>>> df.nunique().execute()
A    3
B    1
dtype: int64
```

```pycon
>>> df.nunique(axis=1).execute()
0    1
1    2
2    2
dtype: int64
```
