# maxframe.dataframe.groupby.GroupBy.aggregate

#### GroupBy.aggregate(func=None, method='auto', \*args, \*\*kwargs)

Aggregate using one or more operations on grouped data.

* **Parameters:**
  * **groupby** (*MaxFrame Groupby*) – Groupby data.
  * **func** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *list-like*) – Aggregation functions.
  * **method** ( *{'auto'* *,*  *'shuffle'* *,*  *'tree'}* *,* *default 'auto'*) – ‘tree’ method provide a better performance, ‘shuffle’ is recommended
    if aggregated result is very large, ‘auto’ will use ‘shuffle’ method
    in distributed mode and use ‘tree’ in local mode.
* **Returns:**
  Aggregated result.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame(
...     {
...         "A": [1, 1, 2, 2],
...         "B": [1, 2, 3, 4],
...         "C": [0.362838, 0.227877, 1.267767, -0.562860],
...     }
... ).execute()
   A  B         C
0  1  1  0.362838
1  1  2  0.227877
2  2  3  1.267767
3  2  4 -0.562860
```

The aggregation is for each column.

```pycon
>>> df.groupby('A').agg('min').execute()
   B         C
A
1  1  0.227877
2  3 -0.562860
```

Multiple aggregations.

```pycon
>>> df.groupby('A').agg(['min', 'max']).execute()
    B             C
  min max       min       max
A
1   1   2  0.227877  0.362838
2   3   4 -0.562860  1.267767
```

Different aggregations per column

```pycon
>>> df.groupby('A').agg({'B': ['min', 'max'], 'C': 'sum'}).execute()
    B             C
  min max       sum
A
1   1   2  0.590715
2   3   4  0.704907
```

To control the output names with different aggregations per column,
MaxFrame supports “named aggregation”

```pycon
>>> from maxframe.dataframe import NamedAgg
>>> df.groupby("A").agg(
...  b_min=NamedAgg(column="B", aggfunc="min"),
...  c_sum=NamedAgg(column="C", aggfunc="sum")).execute()
   b_min     c_sum
A
1      1  0.590715
2      3  0.704907
```
