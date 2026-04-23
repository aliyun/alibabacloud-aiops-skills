# maxframe.dataframe.DataFrame.to_odps_table

#### DataFrame.to_odps_table(table: Table | [str](https://docs.python.org/3/library/stdtypes.html#str), partition: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, partition_col: [None](https://docs.python.org/3/library/constants.html#None) | [str](https://docs.python.org/3/library/stdtypes.html#str) | [List](https://docs.python.org/3/library/typing.html#typing.List)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = None, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False, unknown_as_string: [bool](https://docs.python.org/3/library/functions.html#bool) | [None](https://docs.python.org/3/library/constants.html#None) = True, index: [bool](https://docs.python.org/3/library/functions.html#bool) = True, index_label: [None](https://docs.python.org/3/library/constants.html#None) | [str](https://docs.python.org/3/library/stdtypes.html#str) | [List](https://docs.python.org/3/library/typing.html#typing.List)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = None, lifecycle: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, table_properties: [dict](https://docs.python.org/3/library/stdtypes.html#dict) | [None](https://docs.python.org/3/library/constants.html#None) = None, primary_key: [None](https://docs.python.org/3/library/constants.html#None) | [str](https://docs.python.org/3/library/stdtypes.html#str) | [List](https://docs.python.org/3/library/typing.html#typing.List)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = None, odps_types: [Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None)

Write DataFrame object into a MaxCompute (ODPS) table.

You need to provide the name of the table to write to. If you want to store
data into a specific partitioned of a table, argument partition can be used.
You can also use partition_col to specify DataFrame columns as partition
columns, and data in the DataFrame will be grouped by these columns and
inserted into partitions the values of these columns.

If the table does not exist, to_odps_table will create one.

Column names for indexes is determined by index_label argument. If the
argument is absent, names of the levels is used if they are not None, or
default names will be used. The default name for indexes with only one level
will be index, and for indexes with multiple levels, the name will be
level_x while x is the index of the level.

* **Parameters:**
  * **table** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Name ot the table to write DataFrame into
  * **partition** (*Optional* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *]*) – Spec of the partition to write to, can be ‘pt1=xxx,pt2=yyy’
  * **partition_col** (*Union* *[**None* *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *List* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *]* *]*) – Name of columns in DataFrame as partition columns.
  * **overwrite** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – Overwrite data if the table / partition already exists.
  * **unknown_as_string** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – If True, object type in the DataFrame will be treated as strings.
    Otherwise errors might be raised.
  * **index** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – If True, indexes will be stored. Otherwise they are ignored.
  * **index_label** (*Union* *[**None* *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *List* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *]* *]*) – Specify column names for index levels. If absent, level names or default
    names will be used.
  * **lifecycle** (*Optional* *[*[*int*](https://docs.python.org/3/library/functions.html#int) *]*) – Specify lifecycle of the output table.
  * **table_properties** (*Optional* *[*[*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *]*) – Specify properties of the output table.
  * **primary_key** (*Union* *[**None* *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *List* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *]* *]*) – If provided and target table does not exist, target table
    will be a delta table with columns specified in this argument
    as primary key.
* **Returns:**
  **result** – Stub DataFrame for execution.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Notes

to_odps_table returns a stub object for execution. The result returned is
not reusable.

### Examples
