# maxframe.dataframe.eval

### maxframe.dataframe.eval(expr, parser='maxframe', engine=None, local_dict=None, global_dict=None, resolvers=(), level=0, target=None, inplace=False)

Evaluate a Python expression as a string using various backends.

The following arithmetic operations are supported: `+`, `-`, `*`,
`/`, `**`, `%`, `//` (python engine only) along with the following
boolean operations: `|` (or), `&` (and), and `~` (not).
Additionally, the `'pandas'` parser allows the use of [`and`](https://docs.python.org/3/reference/expressions.html#and),
[`or`](https://docs.python.org/3/reference/expressions.html#or), and [`not`](https://docs.python.org/3/reference/expressions.html#not) with the same semantics as the
corresponding bitwise operators.  [`Series`](https://pandas.pydata.org/docs/reference/api/pandas.Series.html#pandas.Series) and
[`DataFrame`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html#pandas.DataFrame) objects are supported and behave as they would
with plain ol’ Python evaluation.

* **Parameters:**
  * **expr** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The expression to evaluate. This string cannot contain any Python
    [statements](https://docs.python.org/3/reference/simple_stmts.html#simple-statements),
    only Python [expressions](https://docs.python.org/3/reference/simple_stmts.html#expression-statements).
  * **local_dict** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *or* *None* *,* *optional*) – A dictionary of local variables, taken from locals() by default.
  * **global_dict** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *or* *None* *,* *optional*) – A dictionary of global variables, taken from globals() by default.
  * **resolvers** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *dict-like* *or* *None* *,* *optional*) – A list of objects implementing the `__getitem__` special method that
    you can use to inject an additional collection of namespaces to use for
    variable lookup. For example, this is used in the
    [`query()`](maxframe.dataframe.DataFrame.query.md#maxframe.dataframe.DataFrame.query) method to inject the
    `DataFrame.index` and `DataFrame.columns`
    variables that refer to their respective [`DataFrame`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html#pandas.DataFrame)
    instance attributes.
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The number of prior stack frames to traverse and add to the current
    scope. Most users will **not** need to change this parameter.
  * **target** ([*object*](https://docs.python.org/3/library/functions.html#object) *,* *optional* *,* *default None*) – This is the target object for assignment. It is used when there is
    variable assignment in the expression. If so, then target must
    support item assignment with string keys, and if a copy is being
    returned, it must also support .copy().
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If target is provided, and the expression mutates target, whether
    to modify target inplace. Otherwise, return a copy of target with
    the mutation.
* **Return type:**
  ndarray, numeric scalar, [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame), [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – There are many instances where such an error can be raised:
    
      - target=None, but the expression is multiline.
      - The expression is multiline, but not all them have item assignment.
        An example of such an arrangement is this:
    
        a = b + 1
        a + 2
    
        Here, there are expressions on different lines, making it multiline,
        but the last line has no variable assigned to the output of a + 2.
      - inplace=True, but the expression is missing item assignment.
      - Item assignment is provided, but the target does not support
        string item assignment.
      - Item assignment is provided and inplace=False, but the target
        does not support the .copy() method

#### SEE ALSO
[`DataFrame.query`](maxframe.dataframe.DataFrame.query.md#maxframe.dataframe.DataFrame.query)
: Evaluates a boolean expression to query the columns of a frame.

[`DataFrame.eval`](maxframe.dataframe.DataFrame.eval.md#maxframe.dataframe.DataFrame.eval)
: Evaluate a string describing operations on DataFrame columns.

### Notes

The `dtype` of any objects involved in an arithmetic `%` operation are
recursively cast to `float64`.

See the [enhancing performance](https://pandas.pydata.org/docs/user_guide/enhancingperf.html#enhancingperf-eval) documentation for
more details.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({"animal": ["dog", "pig"], "age": [10, 20]})
>>> df.execute()
  animal  age
0    dog   10
1    pig   20
```

We can add a new column using `pd.eval`:

```pycon
>>> md.eval("double_age = df.age * 2", target=df).execute()
  animal  age  double_age
0    dog   10          20
1    pig   20          40
```
