# maxframe.dataframe.Series.quantile

#### Series.quantile(q=0.5, interpolation='linear')

Return value at the given quantile.

* **Parameters:**
  * **q** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array-like* *,* *default 0.5* *(**50% quantile* *)*) – 0 <= q <= 1, the quantile(s) to compute.
  * **interpolation** ( *{'linear'* *,*  *'lower'* *,*  *'higher'* *,*  *'midpoint'* *,*  *'nearest'}*) – 

    This optional parameter specifies the interpolation method to use,
    when the desired quantile lies between two data points i and j:
    > * linear: i + (j - i) \* fraction, where fraction is the
    >   fractional part of the index surrounded by i and j.
    > * lower: i.
    > * higher: j.
    > * nearest: i or j whichever is nearest.
    > * midpoint: (i + j) / 2.
* **Returns:**
  If `q` is an array or a tensor, a Series will be returned where the
  index is `q` and the values are the quantiles, otherwise
  a float will be returned.
* **Return type:**
  [float](https://docs.python.org/3/library/functions.html#float) or [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
`core.window.Rolling.quantile`, [`numpy.percentile`](https://numpy.org/doc/stable/reference/generated/numpy.percentile.html#numpy.percentile)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series([1, 2, 3, 4])
>>> s.quantile(.5).execute()
2.5
>>> s.quantile([.25, .5, .75]).execute()
0.25    1.75
0.50    2.50
0.75    3.25
dtype: float64
```
