# maxframe.dataframe.read_odps_table

### maxframe.dataframe.read_odps_table(table_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | Table, partitions: [None](https://docs.python.org/3/library/constants.html#None) | [str](https://docs.python.org/3/library/stdtypes.html#str) | [List](https://docs.python.org/3/library/typing.html#typing.List)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = None, columns: [List](https://docs.python.org/3/library/typing.html#typing.List)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, index_col: [None](https://docs.python.org/3/library/constants.html#None) | [str](https://docs.python.org/3/library/stdtypes.html#str) | [List](https://docs.python.org/3/library/typing.html#typing.List)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = None, odps_entry: ODPS = None, string_as_binary: [bool](https://docs.python.org/3/library/functions.html#bool) = None, append_partitions: [bool](https://docs.python.org/3/library/functions.html#bool) = False, dtype_backend: [str](https://docs.python.org/3/library/stdtypes.html#str) = None, default_index_type: DefaultIndexType = None, \*\*kw)

Read data from a MaxCompute (ODPS) table into DataFrame.

Supports specifying some columns as indexes. If not specified, RangeIndex
will be generated.

* **Parameters:**
  * **table_name** (*Union* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *Table* *]*) – Name of the table to read from.
  * **partitions** (*Union* *[**None* *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *List* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *]* *]*) – Table partition or list of partitions to read from.
  * **columns** (*Optional* *[**List* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *]* *]*) – Table columns to read from. You may also specify partition columns here.
    If not specified, all table columns (or include partition columns if
    append_partitions is True) will be included.
  * **index_col** (*Union* *[**None* *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *List* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *]* *]*) – Columns to be specified as indexes.
  * **append_partitions** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – If True, will add all partition columns as selected columns when
    columns is not specified,
  * **dtype_backend** ( *{'numpy'* *,*  *'pyarrow'}* *,* *default 'numpy'*) – Back-end data type applied to the resultant DataFrame (still experimental).
* **Returns:**
  **result** – DataFrame read from MaxCompute (ODPS) table
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
