# maxframe.dataframe.DataFrame.corr

#### DataFrame.corr(method='pearson', min_periods=1)

Compute pairwise correlation of columns, excluding NA/null values.

* **Parameters:**
  * **method** ( *{'pearson'* *,*  *'kendall'* *,*  *'spearman'}* *or* *callable*) – 

    Method of correlation:
    * pearson : standard correlation coefficient
    * kendall : Kendall Tau correlation coefficient
    * spearman : Spearman rank correlation
    * callable: callable with input two 1d ndarrays
      : and returning a float. Note that the returned matrix from corr
        will have 1 along the diagonals and will be symmetric
        regardless of the callable’s behavior.

    #### NOTE
    kendall, spearman and callables not supported on multiple chunks yet.
  * **min_periods** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Minimum number of observations required per pair of columns
    to have a valid result. Currently only available for Pearson
    and Spearman correlation.
* **Returns:**
  Correlation matrix.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.corrwith`](maxframe.dataframe.DataFrame.corrwith.md#maxframe.dataframe.DataFrame.corrwith)
: Compute pairwise correlation with another DataFrame or Series.

[`Series.corr`](maxframe.dataframe.Series.corr.md#maxframe.dataframe.Series.corr)
: Compute the correlation between two Series.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([(.2, .3), (.0, .6), (.6, .0), (.2, .1)],
...                   columns=['dogs', 'cats'])
>>> df.corr(method='pearson').execute()
          dogs      cats
dogs  1.000000 -0.851064
cats -0.851064  1.000000
```
