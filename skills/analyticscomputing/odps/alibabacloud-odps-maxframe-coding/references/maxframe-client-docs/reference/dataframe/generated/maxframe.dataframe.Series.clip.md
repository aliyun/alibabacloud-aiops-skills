# maxframe.dataframe.Series.clip

#### Series.clip(lower=None, upper=None, , axis=None, inplace=False)

Trim values at input threshold(s).

Assigns values outside boundary to boundary values. Thresholds
can be singular values or array like, and in the latter case
the clipping is performed element-wise in the specified axis.

* **Parameters:**
  * **lower** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array-like* *,* *default None*) – Minimum threshold value. All values below this
    threshold will be set to it. If None, no lower clipping is performed.
  * **upper** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array-like* *,* *default None*) – Maximum threshold value. All values above this
    threshold will be set to it. If None, no upper clipping is performed.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *str axis name* *,* *optional*) – Align object with lower and upper along the given axis.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether to perform the operation in place on the data.
  * **\*args** – Additional keywords have no effect but might be accepted
    for compatibility with numpy.
  * **\*\*kwargs** – Additional keywords have no effect but might be accepted
    for compatibility with numpy.
* **Returns:**
  Same type as calling object with the values outside the
  clip boundaries replaced or None if `inplace=True`.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) or None

#### SEE ALSO
[`Series.clip`](#maxframe.dataframe.Series.clip)
: Trim values at input threshold in series.

[`DataFrame.clip`](maxframe.dataframe.DataFrame.clip.md#maxframe.dataframe.DataFrame.clip)
: Trim values at input threshold in dataframe.

[`numpy.clip`](https://numpy.org/doc/stable/reference/generated/numpy.clip.html#numpy.clip)
: Clip (limit) the values in an array.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> data = {'col_0': [9, -3, 0, -1, 5], 'col_1': [-2, -7, 6, 8, -5]}
>>> df = md.DataFrame(data)
>>> df.execute()
   col_0  col_1
0      9     -2
1     -3     -7
2      0      6
3     -1      8
4      5     -5
```

Clips per column using lower and upper thresholds:

```pycon
>>> df.clip(lower=-4, upper=7).execute()
   col_0  col_1
0      7     -2
1     -3     -4
2      0      6
3     -1      7
4      5     -4
```

Clips using specific lower and upper thresholds per column element:

```pycon
>>> t = md.Series([2, -4, -1, 6, 3])
>>> t.execute()
0    2
1   -4
2   -1
3    6
4    3
dtype: int64
```

```pycon
>>> df.clip(lower=t, upper=t).execute()
   col_0  col_1
0      2      2
1     -3     -4
2      0     -1
3     -1      6
4      5      3
```
