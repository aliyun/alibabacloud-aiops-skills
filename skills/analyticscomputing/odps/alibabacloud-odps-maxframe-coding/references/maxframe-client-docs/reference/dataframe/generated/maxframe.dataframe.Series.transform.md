# maxframe.dataframe.Series.transform

#### Series.transform(func, convert_dtype=True, axis=0, \*args, skip_infer=False, dtype=None, \*\*kwargs)

Call `func` on self producing a Series with transformed values.

Produced Series will have same axis length as self.

* **Parameters:**
  * **func** (*function* *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *or* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict))
  * **function** ( *-*)
  * **either** (*must*)
  * **Series.apply.** (*work when passed a Series* *or* *when passed to*)
  * **are** (*Accepted combinations*)
  * **function**
  * **name** ( *- string function*)
  * **names** ( *- list* *of* *functions and/or function*)
  * **'sqrt'****]** (*e.g.* *[**np.exp.*)
  * **functions** ( *- dict* *of* *axis labels ->*)
  * **such.** (*function names* *or* *list of*)
  * **axis** ( *{0* *or*  *'index'}*) – Parameter needed for compatibility with DataFrame.
  * **dtype** ([*numpy.dtype*](https://numpy.org/doc/stable/reference/generated/numpy.dtype.html#numpy.dtype) *,* *default None*) – Specify dtypes of returned DataFrames. See Notes for more details.
  * **skip_infer** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether infer dtypes when dtypes or output_type is not specified.
  * **\*args** – Positional arguments to pass to func.
  * **\*\*kwargs** – Keyword arguments to pass to func.
* **Returns:**
  * *Series*
  * *A Series that must have the same length as self.*

:raises ValueError : If the returned Series has a different length than self.:

#### SEE ALSO
[`Series.agg`](maxframe.dataframe.Series.agg.md#maxframe.dataframe.Series.agg)
: Only perform aggregating type operations.

[`Series.apply`](maxframe.dataframe.Series.apply.md#maxframe.dataframe.Series.apply)
: Invoke function on a Series.

### Notes

When deciding output dtypes and shape of the return value, MaxFrame will
try applying `func` onto a mock Series, and the transform call may
fail. When this happens, you need to specify `dtype` of output
Series.

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
