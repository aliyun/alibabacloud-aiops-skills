# maxframe.dataframe.read_odps_query

### maxframe.dataframe.read_odps_query(query: [str](https://docs.python.org/3/library/stdtypes.html#str), odps_entry: ODPS = None, index_col: [None](https://docs.python.org/3/library/constants.html#None) | [str](https://docs.python.org/3/library/stdtypes.html#str) | [List](https://docs.python.org/3/library/typing.html#typing.List)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = None, string_as_binary: [bool](https://docs.python.org/3/library/functions.html#bool) = None, sql_hints: [Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)] = None, anonymous_col_prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) = '_anon_col_', skip_schema: [bool](https://docs.python.org/3/library/functions.html#bool) = False, dtype_backend: [str](https://docs.python.org/3/library/stdtypes.html#str) = None, \*\*kw)

Read data from a MaxCompute (ODPS) query into DataFrame.

Supports specifying some columns as indexes. If not specified, RangeIndex
will be generated.

* **Parameters:**
  * **query** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – MaxCompute SQL statement.
  * **index_col** (*Union* *[**None* *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *List* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *]* *]*) – Columns to be specified as indexes.
  * **string_as_binary** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Whether to convert string columns to binary.
  * **sql_hints** (*Dict* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *]* *,* *optional*) – User specified SQL hints.
  * **anonymous_col_prefix** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Prefix for anonymous columns, ‘_anon_col_’ by default.
  * **skip_schema** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Skip resolving output schema before execution. Once this is configured,
    the output DataFrame cannot be inputs of other DataFrame operators
    before execution.
  * **dtype_backend** ( *{'numpy'* *,*  *'pyarrow'}* *,* *default 'numpy'*) – Back-end data type applied to the resultant DataFrame (still experimental).
* **Returns:**
  **result** – DataFrame read from MaxCompute (ODPS) table
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
