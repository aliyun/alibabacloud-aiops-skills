# maxframe.dataframe.DataFrame.to_parquet

#### DataFrame.to_parquet(path, engine='auto', compression='snappy', index=None, partition_cols=None, storage_options: [dict](https://docs.python.org/3/library/stdtypes.html#dict) = None, \*\*kwargs)

Write a DataFrame to the binary parquet format, each chunk will be
written to a Parquet file.

* **Parameters:**
  * **path** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *file-like object*) – If path is a string with wildcard e.g. ‘/to/path/out-

    ```
    *
    ```

    .parquet’,
    to_parquet will try to write multiple files, for instance,
    chunk (0, 0) will write data into ‘/to/path/out-0.parquet’.
    If path is a string without wildcard and partition_cols is None,
    all data will be written into a single file.
    If path is a string without wildcard or partition_cols is not None,
    we will treat it as a directory.
  * **engine** ( *{'auto'* *,*  *'pyarrow'* *,*  *'fastparquet'}* *,* *default 'auto'*) – Parquet library to use. The default behavior is to try ‘pyarrow’,
    falling back to ‘fastparquet’ if ‘pyarrow’ is unavailable.
  * **compression** ( *{'snappy'* *,*  *'gzip'* *,*  *'brotli'* *,* *None}* *,* *default 'snappy'*) – Name of the compression to use. Use `None` for no compression.
  * **index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default None*) – If `True`, include the dataframe’s index(es) in the file output.
    If `False`, they will not be written to the file.
    If `None`, similar to `True` the dataframe’s index(es)
    will be saved. However, instead of being saved as values,
    the RangeIndex will be stored as a range in the metadata so it
    doesn’t require much space and is faster. Other indexes will
    be included as columns in the file output.
  * **partition_cols** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* *optional* *,* *default None*) – Column names by which to partition the dataset.
    Columns are partitioned in the order they are given.
    Must be None if path is not a string.
  * **\*\*kwargs** – Additional arguments passed to the parquet library.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame(data={'col1': [1, 2], 'col2': [3, 4]})
>>> df.to_parquet('*.parquet.gzip',
...               compression='gzip').execute()
>>> md.read_parquet('*.parquet.gzip').execute()
   col1  col2
0     1     3
1     2     4
```

```pycon
>>> import io
>>> f = io.BytesIO()
>>> df.to_parquet(f).execute()
>>> f.seek(0)
0
>>> content = f.read()
```
