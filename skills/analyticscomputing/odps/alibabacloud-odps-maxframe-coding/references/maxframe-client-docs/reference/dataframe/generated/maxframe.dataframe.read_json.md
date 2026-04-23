# maxframe.dataframe.read_json

### maxframe.dataframe.read_json(path, \*, orient=None, typ='frame', dtype=None, convert_axes=None, lines=False, chunksize=None, compression='infer', index_col=None, usecols=None, chunk_bytes='64M', gpu=None, head_bytes='100k', head_lines=None, default_index_type: ~maxframe.protocol.DefaultIndexType | str = None, use_nullable_dtypes: bool = <no_default>, dtype_backend: str = <no_default>, storage_options: dict = None, memory_scale: int = None, merge_small_files: bool = True, merge_small_file_options: dict = None, session=None, run_kwargs: dict = None, \*\*kwargs)

Read a JSON file into a DataFrame.

* **Parameters:**
  * **path** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *path object* *, or* *file-like object*) – Any valid string path is acceptable. The string could be a URL. Valid
    URL schemes include http, ftp, s3, and file. For file URLs, a host is
    expected. A local file could be: [file://localhost/path/to/table.json](file://localhost/path/to/table.json),
    you can also read from external resources using a URL like:
    hdfs://localhost:8020/test.json.
    If you want to pass in a path object, pandas accepts any `os.PathLike`.
    By file-like object, we refer to objects with a `read()` method, such as
    a file handler (e.g. via builtin `open` function) or `StringIO`.
  * **orient** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – 

    Indication of expected JSON string format.
    Compatible JSON strings can be produced by `to_json()` with a
    corresponding orient value.
    The set of possible orients is:
    - `'split'` : dict like `{'index' -> [index], 'columns' -> [columns], 'data' -> [values]}`
    - `'records'` : list like `[{column -> value}, ... , {column -> value}]`
    - `'index'` : dict like `{index -> {column -> value}}`
    - `'columns'` : dict like `{column -> {index -> value}}`
    - `'values'` : just the values array
    The allowed and default values depend on the value of the typ parameter.
    \* when `typ == 'series'`,
    > - allowed orients are `{'split','records','index'}`
    > - default is `'index'`
    > - The Series index must be unique for orient `'index'`.
    * when `typ == 'frame'`,
      - allowed orients are `{'split','records','index','columns','values'}`
      - default is `'columns'`
      - The DataFrame index must be unique for orients `'index'` and `'columns'`.
      - The DataFrame columns must be unique for orients `'index'`, `'columns'`,
      > and `'records'`.
  * **typ** ( *{{'frame'* *,*  *'series'}}* *,* *default 'frame'*) – The type of object to recover.
  * **dtype** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *or* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *,* *default None*) – If True, infer dtypes; if a dict of column to dtype, then use those;
    if False, then don’t infer dtypes at all, applies only to the data.
  * **convert_axes** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default None*) – Try to convert the axes to the proper dtypes.
  * **convert_dates** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default True*) – List of columns to parse for dates. If True, then try to parse datelike columns.
    A column label is datelike if
    \* it ends with `'_at'`,
    \* it ends with `'_time'`,
    \* it begins with `'date'`, or
    \* it is `'datetime'`, `'timestamp'`, `'modified'`, or `'created'`.
  * **keep_default_dates** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If parsing dates, then parse the default datelike columns.
  * **precise_float** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Set to enable usage of higher precision (strtod) function when
    decoding string to double values. Default (False) is to use fast but
    less precise builtin functionality.
  * **date_unit** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – The timestamp unit to detect if converting dates. The default behaviour
    is to try and detect the correct precision, but if this is not desired
    then pass one of ‘s’, ‘ms’, ‘us’ or ‘ns’ to force parsing only seconds,
    milliseconds, microseconds or nanoseconds respectively.
  * **encoding** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default is 'utf-8'*) – The encoding to use to decode py3 bytes.
  * **lines** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Read the file as a json object per line.
  * **chunksize** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Return JsonReader object for iteration.
    See the [IO Tools docs](https://pandas.pydata.org/pandas-docs/stable/io.html#io-jsonl)
    for more information on `chunksize`.
    This can only be passed if lines=True.
    If this is None, the file will be read into memory all at once.
  * **compression** ( *{{'infer'* *,*  *'gzip'* *,*  *'bz2'* *,*  *'zip'* *,*  *'xz'* *,* *None}}* *,* *default 'infer'*) – For on-the-fly decompression of on-disk data. If ‘infer’ and
    filepath_or_buffer is path-like, then detect compression from the
    following extensions: ‘.gz’, ‘.bz2’, ‘.zip’, or ‘.xz’ (otherwise no
    decompression). If using ‘zip’, the ZIP file must contain only one data
    file to be read in. Set to None for no decompression.
  * **index_col** (int, str, sequence of int / str, or False, default `None`) – Column(s) to use as the row labels of the `DataFrame`, either given as
    string name or column index. If a sequence of int / str is given, a
    MultiIndex is used.
    Note: `index_col=False` can be used to force pandas to *not* use the first
    column as the index, e.g. when you have a malformed file with delimiters at
    the end of each line.
  * **usecols** (*list-like* *or* *callable* *,* *optional*) – Return a subset of the columns. If list-like, all elements must either
    be positional (i.e. integer indices into the document columns) or strings
    that correspond to column names provided either by the user in names or
    inferred from the document header row(s). For example, a valid list-like
    usecols parameter would be `[0, 1, 2]` or `['foo', 'bar', 'baz']`.
    Element order is ignored, so `usecols=[0, 1]` is the same as `[1, 0]`.
    To instantiate a DataFrame from `data` with element order preserved use
    `pd.read_csv(data, usecols=['foo', 'bar'])[['foo', 'bar']]` for columns
    in `['foo', 'bar']` order or
    `pd.read_csv(data, usecols=['foo', 'bar'])[['bar', 'foo']]`
    for `['bar', 'foo']` order.
    If callable, the callable function will be evaluated against the column
    names, returning names where the callable function evaluates to True. An
    example of a valid callable argument would be `lambda x: x.upper() in
    ['AAA', 'BBB', 'DDD']`. Using this parameter results in much faster
    parsing time and lower memory usage.
  * **chunk_bytes** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*float*](https://docs.python.org/3/library/functions.html#float) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Number of chunk bytes.
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If read into cudf DataFrame.
  * **head_bytes** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*float*](https://docs.python.org/3/library/functions.html#float) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Number of bytes to use in the head of file, mainly for data inference.
  * **head_lines** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Number of lines to use in the head of file, mainly for data inference.
  * **default_index_type** ( *{None* *,*  *'range'* *,*  *'incremental'}* *,* *default None*) – If index_col not specified, specify type of index to generate.
    If not specified, options.dataframe.default_index_type will be used.
  * **dtype_backend** ( *{'numpy'* *,*  *'pyarrow'}* *,* *default 'numpy'*) – Back-end data type applied to the resultant DataFrame (still experimental).
  * **storage_options** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *,* *optional*) – Options for storage connection.
  * **merge_small_files** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Merge small files whose size is small.
  * **merge_small_file_options** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict)) – Options for merging small files
* **Returns:**
  A JSON file is returned as two-dimensional data structure with labeled axes.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) or [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
`to_json`
: Convert DataFrame to JSON string.

`json_normalize`
: Normalize semi-structured JSON data into a flat table.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> md.read_json('data.json')
>>> # read from HDFS
>>> md.read_json('hdfs://localhost:8020/test.json')
>>> # read from OSS
>>> md.read_json('oss://oss-cn-hangzhou.aliyuncs.com/bucket/test.json',
>>>             storage_options={'role_arn': 'acs:ram::xxxxxx:role/aliyunodpsdefaultrole'})
```
