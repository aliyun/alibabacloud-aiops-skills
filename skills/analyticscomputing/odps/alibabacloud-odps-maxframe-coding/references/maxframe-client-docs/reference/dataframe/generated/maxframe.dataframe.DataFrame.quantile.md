# maxframe.dataframe.DataFrame.quantile

#### DataFrame.quantile(q=0.5, axis=0, numeric_only=True, interpolation='linear')

Return values at the given quantile over requested axis.

* **Parameters:**
  * **q** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array-like* *,* *default 0.5* *(**50% quantile* *)*) – Value between 0 <= q <= 1, the quantile(s) to compute.
  * **axis** ( *{0* *,* *1* *,*  *'index'* *,*  *'columns'}* *(**default 0* *)*) – Equals 0 or ‘index’ for row-wise, 1 or ‘columns’ for column-wise.
  * **numeric_only** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If False, the quantile of datetime and timedelta data will be
    computed as well.
  * **interpolation** ( *{'linear'* *,*  *'lower'* *,*  *'higher'* *,*  *'midpoint'* *,*  *'nearest'}*) – 

    This optional parameter specifies the interpolation method to use,
    when the desired quantile lies between two data points i and j:
    \* linear: i + (j - i) \* fraction, where fraction is the
    > fractional part of the index surrounded by i and j.
    * lower: i.
    * higher: j.
    * nearest: i or j whichever is nearest.
    * midpoint: (i + j) / 2.
* **Returns:**
  If `q` is an array or a tensor, a DataFrame will be returned where the
  : index is `q`, the columns are the columns of self, and the
    values are the quantiles.

  If `q` is a float, a Series will be returned where the
  : index is the columns of self and the values are the quantiles.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
`core.window.Rolling.quantile`
: Rolling quantile.

[`numpy.percentile`](https://numpy.org/doc/stable/reference/generated/numpy.percentile.html#numpy.percentile)
: Numpy function to compute the percentile.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame(np.array([[1, 1], [2, 10], [3, 100], [4, 100]]),
...                   columns=['a', 'b'])
>>> df.quantile(.1).execute()
a    1.3
b    3.7
Name: 0.1, dtype: float64
```

```pycon
>>> df.quantile([.1, .5]).execute()
       a     b
0.1  1.3   3.7
0.5  2.5  55.0
```
