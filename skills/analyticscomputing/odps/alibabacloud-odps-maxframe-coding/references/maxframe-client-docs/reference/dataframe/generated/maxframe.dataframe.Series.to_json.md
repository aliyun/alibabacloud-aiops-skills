# maxframe.dataframe.Series.to_json

#### Series.to_json(path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, orient: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, date_format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, double_precision: [int](https://docs.python.org/3/library/functions.html#int) = 10, force_ascii: [bool](https://docs.python.org/3/library/functions.html#bool) = True, date_unit: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = 'ms', default_handler: callable | [None](https://docs.python.org/3/library/constants.html#None) = None, lines: [bool](https://docs.python.org/3/library/functions.html#bool) = False, compression: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None) = 'infer', index: [bool](https://docs.python.org/3/library/functions.html#bool) | [None](https://docs.python.org/3/library/constants.html#None) = None, indent: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, storage_options: [Dict](https://docs.python.org/3/library/typing.html#typing.Dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None) = None, partition_cols: [str](https://docs.python.org/3/library/stdtypes.html#str) | [list](https://docs.python.org/3/library/stdtypes.html#list) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*\*kwargs)

Convert the object to a JSON string.

Note NaN’s and None will be converted to null and datetime objects
will be converted to UNIX timestamps.

* **Parameters:**
  * **path** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *path object* *,* *file-like object* *, or* *None* *,* *default None*) – String, path object (implementing os.PathLike[str]), or file-like
    object implementing a write() function. If None, the result is
    returned as a string.
  * **orient** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – 

    Indication of expected JSON string format.
    * Series:
      > - default is ‘index’
      > - allowed values are: {‘split’, ‘records’, ‘index’, ‘table’}.
    * DataFrame:
      > - default is ‘columns’
      > - allowed values are: {‘split’, ‘records’, ‘index’, ‘columns’,
      >   ‘values’, ‘table’}.
    * The format of the JSON string:
      > - ’split’ : dict like {‘index’ -> [index], ‘columns’ -> [columns],
      >   ‘data’ -> [values]}
      > - ’records’ : list like [{column -> value}, … , {column -> value}]
      > - ’index’ : dict like {index -> {column -> value}}
      > - ’columns’ : dict like {column -> {index -> value}}
      > - ’values’ : just the values array
      > - ’table’ : dict like {‘schema’: {schema}, ‘data’: {data}}

      > Describing the data, where data component is like `orient='records'`.
  * **date_format** ( *{None* *,*  *'epoch'* *,*  *'iso'}*) – Type of date conversion. ‘epoch’ = epoch milliseconds,
    ‘iso’ = ISO8601. The default depends on the orient. For
    `orient='table'`, the default is ‘iso’. For all other orients,
    the default is ‘epoch’.
  * **double_precision** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 10*) – The number of decimal places to use when encoding
    floating point numbers.
  * **force_ascii** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Force encoded string to be ASCII.
  * **date_unit** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default 'ms'* *(**milliseconds* *)*) – The time unit to encode to, governs timestamp and ISO8601
    precision.  One of ‘s’, ‘ms’, ‘us’, ‘ns’ for second, millisecond,
    microsecond, and nanosecond respectively.
  * **default_handler** (*callable* *,* *default None*) – Handler to call if object cannot otherwise be converted to a
    suitable format for JSON. Should receive a single argument which is
    the object to convert and return a serializable object.
  * **lines** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If ‘orient’ is ‘records’ write out line-delimited json format. Will
    throw ValueError if incorrect ‘orient’ is used.
  * **compression** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *,* *default 'infer'*) – For on-the-fly compression of the output data. If str, represents
    compression mode. If dict, value at ‘method’ is the compression mode.
    Compression mode may be any of the following possible
    values: {‘infer’, ‘gzip’, ‘bz2’, ‘zip’, ‘xz’, None}. If compression
    mode is ‘infer’ and path_or_buf is path-like, then detect
    compression mode from the following extensions: ‘.gz’, ‘.bz2’,
    ‘.zip’ or ‘.xz’. (otherwise no compression). If dict given and
    mode is one of {‘zip’, ‘xz’}, other entries passed as
    additional compression options.
  * **index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default None*) – Whether to include the index values in the JSON string. Not
    including the index (`index=False`) is only supported when
    orient is ‘split’ or ‘table’.
  * **indent** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Length of whitespace used to indent each record.
  * **partition_cols** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* *optional* *,* *default None*) – Column names by which to partition the dataset.
    Columns are partitioned in the order they are given.

#### SEE ALSO
[`read_json`](maxframe.dataframe.read_json.md#maxframe.dataframe.read_json)
: Convert a JSON string to pandas object.

### Notes

The behavior of `indent=0` varies from the stdlib, which does not
indent the output but does insert newlines. Currently, `indent=0`
and the default `indent=None` are equivalent in pandas, though this
may change in a future release.

`orient='table'` contains a ‘pandas_version’ field under ‘schema’.
This stores the version of pandas used in the latest revision of the
schema.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([['a', 'b'], ['c', 'd']],
...                   index=['row 1', 'row 2'],
...                   columns=['col 1', 'col 2'])
>>> df.to_json('data.json')
>>> # Writing to a file with orient='records'
>>> df.to_json('records.json', orient='records')
>>> # Writing in line-delimited json format
>>> df.to_json('ldjson.json', orient='records', lines=True)
>>> # Write partitioned dataset
>>> df.to_json('dataset', partition_cols=['col 1'])
```
