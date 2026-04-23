# maxframe.dataframe.read_clipboard

### maxframe.dataframe.read_clipboard(sep=None, \*\*kwargs)

Read text from clipboard and pass to [`read_csv()`](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html#pandas.read_csv).

Parses clipboard contents similar to how CSV files are parsed
using [`read_csv()`](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html#pandas.read_csv).

* **Parameters:**
  * **sep** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default 's+'*) – A string or regex delimiter. The default of `'\s+'` denotes
    one or more whitespace characters.
  * **\*\*kwargs** – See [`read_csv()`](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html#pandas.read_csv) for the full argument list.
* **Returns:**
  A parsed [`DataFrame`](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) object.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.to_clipboard`](maxframe.dataframe.DataFrame.to_clipboard.md#maxframe.dataframe.DataFrame.to_clipboard)
: Copy object to the system clipboard.

[`read_csv`](maxframe.dataframe.read_csv.md#maxframe.dataframe.read_csv)
: Read a comma-separated values (csv) file into DataFrame.

`read_fwf`
: Read a table of fixed-width formatted lines into DataFrame.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([[1, 2, 3], [4, 5, 6]], columns=['A', 'B', 'C'])
>>> df.to_clipboard()
>>> md.read_clipboard()
     A  B  C
0    1  2  3
1    4  5  6
```
