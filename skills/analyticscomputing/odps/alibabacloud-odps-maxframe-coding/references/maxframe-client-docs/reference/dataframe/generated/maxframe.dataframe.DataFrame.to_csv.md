# maxframe.dataframe.DataFrame.to_csv

#### DataFrame.to_csv(path, sep=',', na_rep='', float_format=None, columns=None, header=True, index=True, index_label=None, mode='w', encoding=None, compression='infer', quoting=None, quotechar='"', lineterminator=None, chunksize=None, date_format=None, doublequote=True, escapechar=None, decimal='.', partition_cols=None, storage_options=None, \*\*kw)

Write object to a comma-separated values (csv) file.

* **Parameters:**
  * **path** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – File path.
    If path is a string with wildcard e.g. ‘/to/path/out-

    ```
    *
    ```

    .csv’,
    to_csv will try to write multiple files, for instance,
    chunk (0, 0) will write data into ‘/to/path/out-0.csv’.
    If path is a string without wildcard,
    all data will be written into a single file.
  * **sep** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default '* *,* *'*) – String of length 1. Field delimiter for the output file.
  * **na_rep** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default ''*) – Missing data representation.
  * **float_format** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Format string for floating point numbers.
  * **columns** (*sequence* *,* *optional*) – Columns to write.
  * **header** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default True*) – Write out the column names. If a list of strings is given it is
    assumed to be aliases for the column names.
  * **index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Write row names (index).
  * **index_label** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *sequence* *, or* *False* *,* *default None*) – Column label for index column(s) if desired. If None is given, and
    header and index are True, then the index names are used. A
    sequence should be given if the object uses MultiIndex. If
    False do not print fields for index names. Use index_label=False
    for easier importing in R.
  * **mode** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Python write mode, default ‘w’.
  * **encoding** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – A string representing the encoding to use in the output file,
    defaults to ‘utf-8’.
  * **compression** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *,* *default 'infer'*) – If str, represents compression mode. If dict, value at ‘method’ is
    the compression mode. Compression mode may be any of the following
    possible values: {‘infer’, ‘gzip’, ‘bz2’, ‘zip’, ‘xz’, None}. If
    compression mode is ‘infer’ and path_or_buf is path-like, then
    detect compression mode from the following extensions: ‘.gz’,
    ‘.bz2’, ‘.zip’ or ‘.xz’. (otherwise no compression). If dict given
    and mode is ‘zip’ or inferred as ‘zip’, other entries passed as
    additional compression options.
  * **quoting** (*optional constant from csv module*) – Defaults to csv.QUOTE_MINIMAL. If you have set a float_format
    then floats are converted to strings and thus csv.QUOTE_NONNUMERIC
    will treat them as non-numeric.
  * **quotechar** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default '"'*) – String of length 1. Character used to quote fields.
  * **lineterminator** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – The newline character or character sequence to use in the output
    file. Defaults to os.linesep, which depends on the OS in which
    this method is called (’n’ for linux, ‘rn’ for Windows, i.e.).
  * **chunksize** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *None*) – Rows to write at a time.
  * **date_format** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Format string for datetime objects.
  * **doublequote** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Control quoting of quotechar inside a field.
  * **escapechar** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – String of length 1. Character used to escape sep and quotechar
    when appropriate.
  * **decimal** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default '.'*) – Character recognized as decimal separator. E.g. use ‘,’ for
    European data.
  * **partition_cols** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* *optional* *,* *default None*) – Column names by which to partition the dataset.
    Columns are partitioned in the order they are given.
* **Returns:**
  If path_or_buf is None, returns the resulting csv format as a
  string. Otherwise returns None.
* **Return type:**
  None or [str](https://docs.python.org/3/library/stdtypes.html#str)

#### SEE ALSO
[`read_csv`](maxframe.dataframe.read_csv.md#maxframe.dataframe.read_csv)
: Load a CSV file into a DataFrame.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'name': ['Raphael', 'Donatello'],
...                    'mask': ['red', 'purple'],
...                    'weapon': ['sai', 'bo staff']})
>>> df.to_csv('out.csv', index=False).execute()
>>> # Write partitioned dataset
>>> df.to_csv('dataset', partition_cols=['mask']).execute()
```
