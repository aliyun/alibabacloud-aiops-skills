# maxframe.dataframe.groupby.DataFrameGroupBy.mf.apply_chunk

#### DataFrameGroupBy.mf.apply_chunk(func: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Callable](https://docs.python.org/3/library/typing.html#typing.Callable), batch_rows=None, dtypes=None, dtype=None, name=None, output_type=None, index=None, skip_infer=False, order_cols=None, ascending=True, args=(), \*\*kwargs)

Apply function func group-wise and combine the results together.
The pandas DataFrame given to the function is a chunk of the input
dataframe, consider as a batch rows.

The function passed to apply must take a dataframe as its first
argument and return a DataFrame, Series or scalar. apply will
then take care of combining the results back together into a single
dataframe or series. apply is therefore a highly flexible
grouping method.

Don’t expect to receive all rows of the DataFrame in the function,
as it depends on the implementation of MaxFrame and the internal
running state of MaxCompute.

* **Parameters:**
  * **func** (*callable*) – A callable that takes a dataframe as its first argument, and
    returns a dataframe, a series or a scalar. In addition the
    callable may take positional and keyword arguments.
  * **batch_rows** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Specify expected number of rows in a batch, as well as the len of
    function input dataframe. When the remaining data is insufficient,
    it may be less than this number.
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
`Series.apply`
: Apply a function to a Series.

`DataFrame.apply`
: Apply a function to each row or column of a DataFrame.

`DataFrame.mf.apply_chunk`
: Apply a function to row batches of a DataFrame.

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

MaxFrame adopts expected behavior of pandas>=3.0 by ignoring group columns
in user function input. If you still need a group column for your function
input, try selecting it right after groupby results, for instance,
`df.groupby("A")[["A", "B", "C"]].mf.apply_chunk(func)` will pass data of
column A into `func`.
