# maxframe.dataframe.read_parquet

### maxframe.dataframe.read_parquet(path, engine: str = 'auto', columns: list = None, groups_as_chunks: bool = False, dtype_backend: str = <no_default>, default_index_type: ~maxframe.protocol.DefaultIndexType | str = None, storage_options: dict = None, use_nullable_dtypes: bool = <no_default>, \*, dtypes: ~pandas.core.series.Series = None, index_dtypes: ~pandas.core.series.Series = None, memory_scale: int = None, merge_small_files: bool = True, merge_small_file_options: dict = None, gpu: bool = None, session=None, run_kwargs: dict = None, \*\*kwargs)

Load a parquet object from the file path, returning a DataFrame.

* **Parameters:**
  * **path** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *path object* *or* *file-like object*) – Any valid string path is acceptable. The string could be a URL.
    For file URLs, a host is expected. A local file could be:
    `file://localhost/path/to/table.parquet`.
    A file URL can also be a path to a directory that contains multiple
    partitioned parquet files. Both pyarrow and fastparquet support
    paths to directories as well as file URLs. A directory path could be:
    `file://localhost/path/to/tables`.
    By file-like object, we refer to objects with a `read()` method,
    such as a file handler (e.g. via builtin `open` function)
    or `StringIO`.
  * **engine** ( *{'auto'* *,*  *'pyarrow'}* *,* *default 'auto'*) – Parquet library to use. The default behavior is to try ‘pyarrow’,
  * **storage_options** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *,* *optional*) – Options for storage connection.
  * **columns** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* *default=None*) – If not None, only these columns will be read from the file.
  * **groups_as_chunks** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – if True, each row group correspond to a chunk.
    if False, each file correspond to a chunk.
    Only available for ‘pyarrow’ engine.
  * **default_index_type** ( *{None* *,*  *'range'* *,*  *'incremental'}* *,* *default None*) – If index_col not specified, specify type of index to generate.
    If not specified, options.dataframe.default_index_type will be used.
  * **dtype_backend** ( *{'numpy'* *,*  *'pyarrow'}* *,* *default 'numpy'*) – Back-end data type applied to the resultant DataFrame (still experimental).
  * **storage_options** – Options for storage connection.
  * **memory_scale** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Scale that real memory occupation divided with raw file size.
  * **merge_small_files** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Merge small files whose size is small.
  * **\*\*kwargs** – Any additional kwargs are passed to the engine.
* **Return type:**
  MaxFrame DataFrame
