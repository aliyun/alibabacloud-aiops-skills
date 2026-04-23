# maxframe.dataframe.DataFrame.cov

#### DataFrame.cov(min_periods=None, ddof=1, numeric_only=True)

Compute pairwise covariance of columns, excluding NA/null values.

Compute the pairwise covariance among the series of a DataFrame.
The returned data frame is the [covariance matrix](https://en.wikipedia.org/wiki/Covariance_matrix) of the columns
of the DataFrame.

Both NA and null values are automatically excluded from the
calculation. (See the note below about bias from missing values.)
A threshold can be set for the minimum number of
observations for each value created. Comparisons with observations
below this threshold will be returned as `NaN`.

This method is generally used for the analysis of time series data to
understand the relationship between different measures
across time.

* **Parameters:**
  * **min_periods** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Minimum number of observations required per pair of columns
    to have a valid result.
  * **ddof** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 1*) – Delta degrees of freedom.  The divisor used in calculations
    is `N - ddof`, where `N` represents the number of elements.
    This argument is applicable only when no `nan` is in the dataframe.
  * **numeric_only** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Include only float, int or boolean data.
* **Returns:**
  The covariance matrix of the series of the DataFrame.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`Series.cov`](maxframe.dataframe.Series.cov.md#maxframe.dataframe.Series.cov)
: Compute covariance with another Series.

`core.window.ewm.ExponentialMovingWindow.cov`
: Exponential weighted sample covariance.

`core.window.expanding.Expanding.cov`
: Expanding sample covariance.

`core.window.rolling.Rolling.cov`
: Rolling sample covariance.

### Notes

Returns the covariance matrix of the DataFrame’s time series.
The covariance is normalized by N-ddof.

For DataFrames that have Series that are missing data (assuming that
data is [missing at random](https://en.wikipedia.org/wiki/Missing_data#Missing_at_random))
the returned covariance matrix will be an unbiased estimate
of the variance and covariance between the member Series.

However, for many applications this estimate may not be acceptable
because the estimate covariance matrix is not guaranteed to be positive
semi-definite. This could lead to estimate correlations having
absolute values which are greater than one, and/or a non-invertible
covariance matrix. See [Estimation of covariance matrices](https://en.wikipedia.org/w/index.php?title=Estimation_of_covariance_matrices) for more details.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([(1, 2), (0, 3), (2, 0), (1, 1)],
...                   columns=['dogs', 'cats'])
>>> df.cov().execute()
          dogs      cats
dogs  0.666667 -1.000000
cats -1.000000  1.666667
```

```pycon
>>> mt.random.seed(42)
>>> df = md.DataFrame(mt.random.randn(1000, 5),
...                   columns=['a', 'b', 'c', 'd', 'e'])
>>> df.cov().execute()
          a         b         c         d         e
a  0.998438 -0.020161  0.059277 -0.008943  0.014144
b -0.020161  1.059352 -0.008543 -0.024738  0.009826
c  0.059277 -0.008543  1.010670 -0.001486 -0.000271
d -0.008943 -0.024738 -0.001486  0.921297 -0.013692
e  0.014144  0.009826 -0.000271 -0.013692  0.977795
```

**Minimum number of periods**

This method also supports an optional `min_periods` keyword
that specifies the required minimum number of non-NA observations for
each column pair in order to have a valid result:

```pycon
>>> mt.random.seed(42)
>>> df = md.DataFrame(mt.random.randn(20, 3),
...                   columns=['a', 'b', 'c'])
>>> df.loc[df.index[:5], 'a'] = mt.nan
>>> df.loc[df.index[5:10], 'b'] = mt.nan
>>> df.cov(min_periods=12).execute()
          a         b         c
a  0.316741       NaN -0.150812
b       NaN  1.248003  0.191417
c -0.150812  0.191417  0.895202
```
