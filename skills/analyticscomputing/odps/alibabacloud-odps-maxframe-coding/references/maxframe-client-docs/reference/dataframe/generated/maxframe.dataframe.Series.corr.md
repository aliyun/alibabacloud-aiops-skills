# maxframe.dataframe.Series.corr

#### Series.corr(other, method='pearson', min_periods=None)

Compute correlation with other Series, excluding missing values.

* **Parameters:**
  * **other** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – Series with which to compute the correlation.
  * **method** ( *{'pearson'* *,*  *'kendall'* *,*  *'spearman'}* *or* *callable*) – 

    Method used to compute correlation:
    - pearson : Standard correlation coefficient
    - kendall : Kendall Tau correlation coefficient
    - spearman : Spearman rank correlation
    - callable: Callable with input two 1d ndarrays and returning a float.

    #### NOTE
    kendall, spearman and callables not supported on multiple chunks yet.
  * **min_periods** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Minimum number of observations needed to have a valid result.
* **Returns:**
  Correlation with other.
* **Return type:**
  [float](https://docs.python.org/3/library/functions.html#float)

#### SEE ALSO
[`DataFrame.corr`](maxframe.dataframe.DataFrame.corr.md#maxframe.dataframe.DataFrame.corr)
: Compute pairwise correlation between columns.

[`DataFrame.corrwith`](maxframe.dataframe.DataFrame.corrwith.md#maxframe.dataframe.DataFrame.corrwith)
: Compute pairwise correlation with another DataFrame or Series.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s1 = md.Series([.2, .0, .6, .2])
>>> s2 = md.Series([.3, .6, .0, .1])
>>> s1.corr(s2, method='pearson').execute()
-0.8510644963469898
```
