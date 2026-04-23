# maxframe.dataframe.DataFrame.corrwith

#### DataFrame.corrwith(other, axis=0, drop=False, method='pearson')

Compute pairwise correlation.

Pairwise correlation is computed between rows or columns of
DataFrame with rows or columns of Series or DataFrame. DataFrames
are first aligned along both axes before computing the
correlations.

* **Parameters:**
  * **other** ([*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) *,* [*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – Object with which to compute correlations.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – The axis to use. 0 or ‘index’ to compute column-wise, 1 or ‘columns’ for
    row-wise.
  * **drop** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Drop missing indices from result.
  * **method** ( *{'pearson'* *,*  *'kendall'* *,*  *'spearman'}* *or* *callable*) – 

    Method of correlation:
    * pearson : standard correlation coefficient
    * kendall : Kendall Tau correlation coefficient
    * spearman : Spearman rank correlation
    * callable: callable with input two 1d ndarrays
      : and returning a float.

    #### NOTE
    kendall, spearman and callables not supported on multiple chunks yet.
* **Returns:**
  Pairwise correlations.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`DataFrame.corr`](maxframe.dataframe.DataFrame.corr.md#maxframe.dataframe.DataFrame.corr)
: Compute pairwise correlation of columns.
