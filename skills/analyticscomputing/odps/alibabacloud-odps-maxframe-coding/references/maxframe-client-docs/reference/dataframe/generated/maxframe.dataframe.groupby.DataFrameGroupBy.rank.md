# maxframe.dataframe.groupby.DataFrameGroupBy.rank

#### DataFrameGroupBy.rank(method='average', ascending=True, na_option='keep', pct=False)

Provide the rank of values within each group.

* **Parameters:**
  * **method** ( *{'average'* *,*  *'min'* *,*  *'max'* *,*  *'first'* *,*  *'dense'}* *,* *default 'average'*) – 
    * average: average rank of group.
    * min: lowest rank in group.
    * max: highest rank in group.
    * first: ranks assigned in order they appear in the array.
    * dense: like ‘min’, but rank always increases by 1 between groups.
  * **ascending** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – False for ranks by high (1) to low (N).
  * **na_option** ( *{'keep'* *,*  *'top'* *,*  *'bottom'}* *,* *default 'keep'*) – 
    * keep: leave NA values where they are.
    * top: smallest rank if ascending.
    * bottom: smallest rank if descending.
  * **pct** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Compute percentage rank of data within each group.
* **Return type:**
  DataFrame with ranking of values within each group

#### SEE ALSO
`Series.groupby`
: Apply a function groupby to a Series.

`DataFrame.groupby`
: Apply a function groupby to each row or column of a DataFrame.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame(
...     {
...         "group": ["a", "a", "a", "a", "a", "b", "b", "b", "b", "b"],
...         "value": [2, 4, 2, 3, 5, 1, 2, 4, 1, 5],
...     }
... )
>>> df.execute()
  group  value
0     a      2
1     a      4
2     a      2
3     a      3
4     a      5
5     b      1
6     b      2
7     b      4
8     b      1
9     b      5
>>> for method in ['average', 'min', 'max', 'dense', 'first']:
...     df[f'{method}_rank'] = df.groupby('group')['value'].rank(method)
>>> df.execute()
  group  value  average_rank  min_rank  max_rank  dense_rank  first_rank
0     a      2           1.5       1.0       2.0         1.0         1.0
1     a      4           4.0       4.0       4.0         3.0         4.0
2     a      2           1.5       1.0       2.0         1.0         2.0
3     a      3           3.0       3.0       3.0         2.0         3.0
4     a      5           5.0       5.0       5.0         4.0         5.0
5     b      1           1.5       1.0       2.0         1.0         1.0
6     b      2           3.0       3.0       3.0         2.0         3.0
7     b      4           4.0       4.0       4.0         3.0         4.0
8     b      1           1.5       1.0       2.0         1.0         2.0
9     b      5           5.0       5.0       5.0         4.0         5.0
```
