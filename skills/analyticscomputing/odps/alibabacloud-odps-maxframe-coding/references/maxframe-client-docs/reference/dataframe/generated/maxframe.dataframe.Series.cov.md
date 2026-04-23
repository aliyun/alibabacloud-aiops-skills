# maxframe.dataframe.Series.cov

#### Series.cov(other, min_periods=None, ddof=1)

Compute covariance with Series, excluding missing values.

The two Series objects are not required to be the same length and
will be aligned internally before the covariance is calculated.

* **Parameters:**
  * **other** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – Series with which to compute the covariance.
  * **min_periods** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Minimum number of observations needed to have a valid result.
  * **ddof** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 1*) – Delta degrees of freedom.  The divisor used in calculations
    is `N - ddof`, where `N` represents the number of elements.
* **Returns:**
  Covariance between Series and other normalized by N-1
  (unbiased estimator).
* **Return type:**
  [float](https://docs.python.org/3/library/functions.html#float)

#### SEE ALSO
[`DataFrame.cov`](maxframe.dataframe.DataFrame.cov.md#maxframe.dataframe.DataFrame.cov)
: Compute pairwise covariance of columns.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s1 = md.Series([0.90010907, 0.13484424, 0.62036035])
>>> s2 = md.Series([0.12528585, 0.26962463, 0.51111198])
>>> s1.cov(s2).execute()
-0.01685762652715874
```
