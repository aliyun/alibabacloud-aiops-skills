<a id="generated-groupby"></a>

# GroupBy

GroupBy objects are returned by groupby
calls: [`maxframe.dataframe.DataFrame.groupby()`](generated/maxframe.dataframe.DataFrame.groupby.md#maxframe.dataframe.DataFrame.groupby), [`maxframe.dataframe.Series.groupby()`](generated/maxframe.dataframe.Series.groupby.md#maxframe.dataframe.Series.groupby), etc.

## Indexing, iteration

## Function application

| [`GroupBy.apply`](generated/maxframe.dataframe.groupby.GroupBy.apply.md#maxframe.dataframe.groupby.GroupBy.apply)(func, \*args[, output_type, ...])            | Apply function func group-wise and combine the results together.                                                                                                        |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`GroupBy.agg`](generated/maxframe.dataframe.groupby.GroupBy.agg.md#maxframe.dataframe.groupby.GroupBy.agg)([func, method])                                    | Aggregate using one or more operations on grouped data.                                                                                                                 |
| [`GroupBy.aggregate`](generated/maxframe.dataframe.groupby.GroupBy.aggregate.md#maxframe.dataframe.groupby.GroupBy.aggregate)([func, method])                  | Aggregate using one or more operations on grouped data.                                                                                                                 |
| [`GroupBy.transform`](generated/maxframe.dataframe.groupby.GroupBy.transform.md#maxframe.dataframe.groupby.GroupBy.transform)(f, \*args[, dtypes, dtype, ...]) | Call function producing a like-indexed DataFrame on each group and return a DataFrame having the same indexes as the original object filled with the transformed values |

## Computations / descriptive stats

| [`GroupBy.all`](generated/maxframe.dataframe.groupby.GroupBy.all.md#maxframe.dataframe.groupby.GroupBy.all)(\*\*kw)                                      |                                                                           |
|----------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`GroupBy.any`](generated/maxframe.dataframe.groupby.GroupBy.any.md#maxframe.dataframe.groupby.GroupBy.any)(\*\*kw)                                      |                                                                           |
| [`GroupBy.cumcount`](generated/maxframe.dataframe.groupby.GroupBy.cumcount.md#maxframe.dataframe.groupby.GroupBy.cumcount)([ascending])                  | Number each item in each group from 0 to the length of that group - 1.    |
| [`GroupBy.cummax`](generated/maxframe.dataframe.groupby.GroupBy.cummax.md#maxframe.dataframe.groupby.GroupBy.cummax)()                                   | Cumulative max for each group.                                            |
| [`GroupBy.cummin`](generated/maxframe.dataframe.groupby.GroupBy.cummin.md#maxframe.dataframe.groupby.GroupBy.cummin)()                                   | Cumulative min for each group.                                            |
| [`GroupBy.cumprod`](generated/maxframe.dataframe.groupby.GroupBy.cumprod.md#maxframe.dataframe.groupby.GroupBy.cumprod)()                                | Cumulative prod for each group.                                           |
| [`GroupBy.cumsum`](generated/maxframe.dataframe.groupby.GroupBy.cumsum.md#maxframe.dataframe.groupby.GroupBy.cumsum)()                                   | Cumulative sum for each group.                                            |
| [`GroupBy.count`](generated/maxframe.dataframe.groupby.GroupBy.count.md#maxframe.dataframe.groupby.GroupBy.count)(\*\*kw)                                |                                                                           |
| [`GroupBy.expanding`](generated/maxframe.dataframe.groupby.GroupBy.expanding.md#maxframe.dataframe.groupby.GroupBy.expanding)([min_periods, shift, ...]) | Return an expanding grouper, providing expanding functionality per group. |
| [`GroupBy.max`](generated/maxframe.dataframe.groupby.GroupBy.max.md#maxframe.dataframe.groupby.GroupBy.max)(\*\*kw)                                      |                                                                           |
| [`GroupBy.mean`](generated/maxframe.dataframe.groupby.GroupBy.mean.md#maxframe.dataframe.groupby.GroupBy.mean)(\*\*kw)                                   |                                                                           |
| [`GroupBy.median`](generated/maxframe.dataframe.groupby.GroupBy.median.md#maxframe.dataframe.groupby.GroupBy.median)(\*\*kw)                             |                                                                           |
| [`GroupBy.min`](generated/maxframe.dataframe.groupby.GroupBy.min.md#maxframe.dataframe.groupby.GroupBy.min)(\*\*kw)                                      |                                                                           |
| [`GroupBy.rolling`](generated/maxframe.dataframe.groupby.GroupBy.rolling.md#maxframe.dataframe.groupby.GroupBy.rolling)(window[, min_periods, ...])      | Return a rolling grouper, providing rolling functionality per group.      |
| [`GroupBy.size`](generated/maxframe.dataframe.groupby.GroupBy.size.md#maxframe.dataframe.groupby.GroupBy.size)(\*\*kw)                                   |                                                                           |
| [`GroupBy.sem`](generated/maxframe.dataframe.groupby.GroupBy.sem.md#maxframe.dataframe.groupby.GroupBy.sem)(\*\*kw)                                      |                                                                           |
| [`GroupBy.std`](generated/maxframe.dataframe.groupby.GroupBy.std.md#maxframe.dataframe.groupby.GroupBy.std)(\*\*kw)                                      |                                                                           |
| [`GroupBy.sum`](generated/maxframe.dataframe.groupby.GroupBy.sum.md#maxframe.dataframe.groupby.GroupBy.sum)(\*\*kw)                                      |                                                                           |
| [`GroupBy.var`](generated/maxframe.dataframe.groupby.GroupBy.var.md#maxframe.dataframe.groupby.GroupBy.var)(\*\*kw)                                      |                                                                           |

The following methods are available in both `SeriesGroupBy` and
`DataFrameGroupBy` objects, but may differ slightly, usually in that
the `DataFrameGroupBy` version usually permits the specification of an
axis argument, and often an argument indicating whether to restrict
application to columns of a specific data type.

| [`DataFrameGroupBy.count`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.count.md#maxframe.dataframe.groupby.DataFrameGroupBy.count)(\*\*kw)                     |                                                  |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------|
| [`DataFrameGroupBy.nunique`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.nunique.md#maxframe.dataframe.groupby.DataFrameGroupBy.nunique)(\*\*kw)               |                                                  |
| [`DataFrameGroupBy.cummax`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.cummax.md#maxframe.dataframe.groupby.DataFrameGroupBy.cummax)()                        | Cumulative max for each group.                   |
| [`DataFrameGroupBy.cummin`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.cummin.md#maxframe.dataframe.groupby.DataFrameGroupBy.cummin)()                        | Cumulative min for each group.                   |
| [`DataFrameGroupBy.cumprod`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.cumprod.md#maxframe.dataframe.groupby.DataFrameGroupBy.cumprod)()                     | Cumulative prod for each group.                  |
| [`DataFrameGroupBy.cumsum`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.cumsum.md#maxframe.dataframe.groupby.DataFrameGroupBy.cumsum)()                        | Cumulative sum for each group.                   |
| [`DataFrameGroupBy.fillna`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.fillna.md#maxframe.dataframe.groupby.DataFrameGroupBy.fillna)([value, method, ...])    | Fill NA/NaN values using the specified method    |
| [`DataFrameGroupBy.idxmax`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.idxmax.md#maxframe.dataframe.groupby.DataFrameGroupBy.idxmax)(\*\*kw)                  |                                                  |
| [`DataFrameGroupBy.idxmin`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.idxmin.md#maxframe.dataframe.groupby.DataFrameGroupBy.idxmin)(\*\*kw)                  |                                                  |
| [`DataFrameGroupBy.nunique`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.nunique.md#maxframe.dataframe.groupby.DataFrameGroupBy.nunique)(\*\*kw)               |                                                  |
| [`DataFrameGroupBy.rank`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.rank.md#maxframe.dataframe.groupby.DataFrameGroupBy.rank)([method, ascending, ...])      | Provide the rank of values within each group.    |
| [`DataFrameGroupBy.sample`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.sample.md#maxframe.dataframe.groupby.DataFrameGroupBy.sample)([n, frac, replace, ...]) | Return a random sample of items from each group. |

The following methods are available only for `SeriesGroupBy` objects.

The following methods are available only for `DataFrameGroupBy` objects.

| [`DataFrameGroupBy.mf.apply_chunk`](generated/maxframe.dataframe.groupby.DataFrameGroupBy.mf.apply_chunk.md#maxframe.dataframe.groupby.DataFrameGroupBy.mf.apply_chunk)(func[, ...])   | Apply function func group-wise and combine the results together.   |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
