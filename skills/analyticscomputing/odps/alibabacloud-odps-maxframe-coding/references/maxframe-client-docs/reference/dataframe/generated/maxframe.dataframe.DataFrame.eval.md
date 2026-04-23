# maxframe.dataframe.DataFrame.eval

#### DataFrame.eval(expr, inplace=False, \*\*kwargs)

Evaluate a string describing operations on DataFrame columns.

Operates on columns only, not specific rows or elements.  This allows
eval to run arbitrary code, which can make you vulnerable to code
injection if you pass user input to this function.

* **Parameters:**
  * **expr** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The expression string to evaluate.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If the expression contains an assignment, whether to perform the
    operation inplace and mutate the existing DataFrame. Otherwise,
    a new DataFrame is returned.
  * **\*\*kwargs** – See the documentation for [`eval()`](maxframe.dataframe.eval.md#maxframe.dataframe.eval) for complete details
    on the keyword arguments accepted by
    [`query()`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.query.html#pandas.DataFrame.query).
* **Returns:**
  The result of the evaluation.
* **Return type:**
  ndarray, scalar, or pandas object

#### SEE ALSO
[`DataFrame.query`](maxframe.dataframe.DataFrame.query.md#maxframe.dataframe.DataFrame.query)
: Evaluates a boolean expression to query the columns of a frame.

[`DataFrame.assign`](maxframe.dataframe.DataFrame.assign.md#maxframe.dataframe.DataFrame.assign)
: Can evaluate an expression or function to create new values for a column.

[`eval`](maxframe.dataframe.eval.md#maxframe.dataframe.eval)
: Evaluate a Python expression as a string using various backends.

### Notes

For more details see the API documentation for [`eval()`](maxframe.dataframe.eval.md#maxframe.dataframe.eval).
For detailed examples see [enhancing performance with eval](https://pandas.pydata.org/docs/user_guide/enhancingperf.html#enhancingperf-eval).

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'A': range(1, 6), 'B': range(10, 0, -2)})
>>> df.execute()
   A   B
0  1  10
1  2   8
2  3   6
3  4   4
4  5   2
>>> df.eval('A + B').execute()
0    11
1    10
2     9
3     8
4     7
dtype: int64
```

Assignment is allowed though by default the original DataFrame is not
modified.

```pycon
>>> df.eval('C = A + B').execute()
   A   B   C
0  1  10  11
1  2   8  10
2  3   6   9
3  4   4   8
4  5   2   7
>>> df.execute()
   A   B
0  1  10
1  2   8
2  3   6
3  4   4
4  5   2
```

Use `inplace=True` to modify the original DataFrame.

```pycon
>>> df.eval('C = A + B', inplace=True)
>>> df.execute()
   A   B   C
0  1  10  11
1  2   8  10
2  3   6   9
3  4   4   8
4  5   2   7
```

Multiple columns can be assigned to using multi-line expressions:

```pycon
>>> df.eval('''
... C = A + B
... D = A - B
... ''').execute()
   A   B   C  D
0  1  10  11 -9
1  2   8  10 -6
2  3   6   9 -3
3  4   4   8  0
4  5   2   7  3
```
