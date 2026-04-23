# maxframe.dataframe.groupby.GroupBy.apply

#### GroupBy.apply(func, \*args, output_type=None, dtypes=None, dtype=None, name=None, index=None, skip_infer=None, \*\*kwargs)

Apply function func group-wise and combine the results together.

The function passed to apply must take a dataframe as its first
argument and return a DataFrame, Series or scalar. apply will
then take care of combining the results back together into a single
dataframe or series. apply is therefore a highly flexible
grouping method.

While apply is a very flexible method, its downside is that
using it can be quite a bit slower than using more specific methods
like agg or transform. Pandas offers a wide range of method that will
be much faster than using apply for their specific purposes, so try to
use them before reaching for apply.

* **Parameters:**
  * **func** (*callable*) – A callable that takes a dataframe as its first argument, and
    returns a dataframe, a series or a scalar. In addition the
    callable may take positional and keyword arguments.
  * **output_type** ( *{'dataframe'* *,*  *'series'}* *,* *default None*) – Specify type of returned object. See Notes for more details.
  * **dtypes** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *,* *default None*) – Specify dtypes of returned DataFrames. See Notes for more details.
  * **dtype** ([*numpy.dtype*](https://numpy.org/doc/stable/reference/generated/numpy.dtype.html#numpy.dtype) *,* *default None*) – Specify dtype of returned Series. See Notes for more details.
  * **name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Specify name of returned Series. See Notes for more details.
  * **index** ([*Index*](maxframe.dataframe.Index.md#maxframe.dataframe.Index) *,* *default None*) – Specify index of returned object. See Notes for more details.
  * **skip_infer** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether infer dtypes when dtypes or output_type is not specified.
  * **args** (*tuple and dict*) – Optional positional and keyword arguments to pass to func.
  * **kwargs** (*tuple and dict*) – Optional positional and keyword arguments to pass to func.
* **Returns:**
  **applied**
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
`pipe`
: Apply function to the full GroupBy object instead of to each group.

[`aggregate`](maxframe.dataframe.groupby.GroupBy.aggregate.md#maxframe.dataframe.groupby.GroupBy.aggregate)
: Apply aggregate function to the GroupBy object.

[`transform`](maxframe.dataframe.groupby.GroupBy.transform.md#maxframe.dataframe.groupby.GroupBy.transform)
: Apply function column-by-column to the GroupBy object.

`Series.apply`
: Apply a function to a Series.

`DataFrame.apply`
: Apply a function to each row or column of a DataFrame.

### Notes

When deciding output dtypes and shape of the return value, MaxFrame will
try applying `func` onto a mock grouped object, and the apply call
may fail. When this happens, you need to specify the type of apply
call (DataFrame or Series) in output_type.

* For DataFrame output, you need to specify a list or a pandas Series
  as `dtypes` of output DataFrame. `index` of output can also be
  specified.
* For Series output, you need to specify `dtype` and `name` of
  output Series.
