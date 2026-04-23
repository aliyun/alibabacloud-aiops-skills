# maxframe.dataframe.Series.value_counts

#### Series.value_counts(normalize=False, sort=True, ascending=False, bins=None, dropna=True, method='auto')

Return a Series containing counts of unique values.

The resulting object will be in descending order so that the
first element is the most frequently-occurring element.
Excludes NA values by default.

* **Parameters:**
  * **normalize** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True then the object returned will contain the relative
    frequencies of the unique values.
  * **sort** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Sort by frequencies.
  * **ascending** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Sort in ascending order.
  * **bins** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Rather than count values, group them into half-open bins,
    a convenience for `pd.cut`, only works with numeric data.
  * **dropna** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Don’t include counts of NaN.
  * **method** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default 'auto'*) – ‘auto’, ‘shuffle’, or ‘tree’, ‘tree’ method provide
    a better performance, while ‘shuffle’ is recommended
    if aggregated result is very large, ‘auto’ will use
    ‘shuffle’ method in distributed mode and use ‘tree’
    in local mode.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Series.count`](maxframe.dataframe.Series.count.md#maxframe.dataframe.Series.count)
: Number of non-NA elements in a Series.

[`DataFrame.count`](maxframe.dataframe.DataFrame.count.md#maxframe.dataframe.DataFrame.count)
: Number of non-NA elements in a DataFrame.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> import numpy as np
>>> s = md.Series([3, 1, 2, 3, 4, np.nan])
>>> s.value_counts().execute()
3.0    2
4.0    1
2.0    1
1.0    1
dtype: int64
```

With normalize set to True, returns the relative frequency by
dividing all values by the sum of values.

```pycon
>>> s = md.Series([3, 1, 2, 3, 4, np.nan])
>>> s.value_counts(normalize=True).execute()
3.0    0.4
4.0    0.2
2.0    0.2
1.0    0.2
dtype: float64
```

**dropna**

With dropna set to False we can also see NaN index values.

```pycon
>>> s.value_counts(dropna=False).execute()
3.0    2
NaN    1
4.0    1
2.0    1
1.0    1
dtype: int64
```
