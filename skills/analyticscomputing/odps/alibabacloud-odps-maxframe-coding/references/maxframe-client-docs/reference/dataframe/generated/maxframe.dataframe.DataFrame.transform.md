# maxframe.dataframe.DataFrame.transform

#### DataFrame.transform(func, axis=0, \*args, dtypes=None, skip_infer=False, \*\*kwargs)

Call `func` on self producing a DataFrame with transformed values.

Produced DataFrame will have same axis length as self.

* **Parameters:**
  * **func** (*function* *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *or* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict)) – 

    Function to use for transforming the data. If a function, must either
    work when passed a DataFrame or when passed to DataFrame.apply.

    Accepted combinations are:
    - function
    - string function name
    - list of functions and/or function names, e.g. `[np.exp. 'sqrt']`
    - dict of axis labels -> functions, function names or list of such.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – If 0 or ‘index’: apply function to each column.
    If 1 or ‘columns’: apply function to each row.
  * **dtypes** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *,* *default None*) – Specify dtypes of returned DataFrames. See Notes for more details.
  * **skip_infer** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether infer dtypes when dtypes or output_type is not specified.
  * **\*args** – Positional arguments to pass to func.
  * **\*\*kwargs** – Keyword arguments to pass to func.
* **Returns:**
  A DataFrame that must have the same length as self.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

:raises ValueError : If the returned DataFrame has a different length than self.:

#### SEE ALSO
[`DataFrame.agg`](maxframe.dataframe.DataFrame.agg.md#maxframe.dataframe.DataFrame.agg)
: Only perform aggregating type operations.

[`DataFrame.apply`](maxframe.dataframe.DataFrame.apply.md#maxframe.dataframe.DataFrame.apply)
: Invoke function on a DataFrame.

### Notes

When deciding output dtypes and shape of the return value, MaxFrame will
try applying `func` onto a mock DataFrame and the apply call may
fail. When this happens, you need to specify a list or a pandas
Series as `dtypes` of output DataFrame.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'A': range(3), 'B': range(1, 4)})
>>> df.execute()
   A  B
0  0  1
1  1  2
2  2  3
>>> df.transform(lambda x: x + 1).execute()
   A  B
0  1  2
1  2  3
2  3  4
```
