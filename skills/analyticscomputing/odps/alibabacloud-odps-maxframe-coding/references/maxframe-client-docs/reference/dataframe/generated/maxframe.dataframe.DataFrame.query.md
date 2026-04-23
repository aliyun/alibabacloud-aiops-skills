# maxframe.dataframe.DataFrame.query

#### DataFrame.query(expr, inplace=False, \*\*kwargs)

Query the columns of a DataFrame with a boolean expression.

* **Parameters:**
  * **expr** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – 

    The query string to evaluate.

    You can refer to variables
    in the environment by prefixing them with an ‘@’ character like
    `@a + b`.

    You can refer to column names that contain spaces or operators by
    surrounding them in backticks. This way you can also escape
    names that start with a digit, or those that  are a Python keyword.
    Basically when it is not valid Python identifier. See notes down
    for more details.

    For example, if one of your columns is called `a a` and you want
    to sum it with `b`, your query should be ``a a` + b`.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – Whether the query should modify the data in place or return
    a modified copy.
  * **\*\*kwargs** – See the documentation for [`eval()`](maxframe.dataframe.eval.md#maxframe.dataframe.eval) for complete details
    on the keyword arguments accepted by [`DataFrame.query()`](#maxframe.dataframe.DataFrame.query).
* **Returns:**
  DataFrame resulting from the provided query expression.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`eval`](maxframe.dataframe.eval.md#maxframe.dataframe.eval)
: Evaluate a string describing operations on DataFrame columns.

[`DataFrame.eval`](maxframe.dataframe.DataFrame.eval.md#maxframe.dataframe.DataFrame.eval)
: Evaluate a string describing operations on DataFrame columns.

### Notes

The result of the evaluation of this expression is first passed to
[`DataFrame.loc`](maxframe.dataframe.DataFrame.loc.md#maxframe.dataframe.DataFrame.loc) and if that fails because of a
multidimensional key (e.g., a DataFrame) then the result will be passed
to `DataFrame.__getitem__()`.

This method uses the top-level [`eval()`](maxframe.dataframe.eval.md#maxframe.dataframe.eval) function to
evaluate the passed query.

The [`query()`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.query.html#pandas.DataFrame.query) method uses a slightly
modified Python syntax by default. For example, the `&` and `|`
(bitwise) operators have the precedence of their boolean cousins,
[`and`](https://docs.python.org/3/reference/expressions.html#and) and [`or`](https://docs.python.org/3/reference/expressions.html#or). This *is* syntactically valid Python,
however the semantics are different.

You can change the semantics of the expression by passing the keyword
argument `parser='python'`. This enforces the same semantics as
evaluation in Python space. Likewise, you can pass `engine='python'`
to evaluate an expression using Python itself as a backend. This is not
recommended as it is inefficient compared to using `numexpr` as the
engine.

The [`DataFrame.index`](maxframe.dataframe.DataFrame.index.md#maxframe.dataframe.DataFrame.index) and
[`DataFrame.columns`](maxframe.dataframe.DataFrame.columns.md#maxframe.dataframe.DataFrame.columns) attributes of the
[`DataFrame`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html#pandas.DataFrame) instance are placed in the query namespace
by default, which allows you to treat both the index and columns of the
frame as a column in the frame.
The identifier `index` is used for the frame index; you can also
use the name of the index to identify it in a query. Please note that
Python keywords may not be used as identifiers.

For further details and examples see the `query` documentation in
[indexing](https://pandas.pydata.org/docs/user_guide/indexing.html#indexing-query).

*Backtick quoted variables*

Backtick quoted variables are parsed as literal Python code and
are converted internally to a Python valid identifier.
This can lead to the following problems.

During parsing a number of disallowed characters inside the backtick
quoted string are replaced by strings that are allowed as a Python identifier.
These characters include all operators in Python, the space character, the
question mark, the exclamation mark, the dollar sign, and the euro sign.
For other characters that fall outside the ASCII range (U+0001..U+007F)
and those that are not further specified in PEP 3131,
the query parser will raise an error.
This excludes whitespace different than the space character,
but also the hashtag (as it is used for comments) and the backtick
itself (backtick can also not be escaped).

In a special case, quotes that make a pair around a backtick can
confuse the parser.
For example, ``it's` > `that's`` will raise an error,
as it forms a quoted string (`'s > `that'`) with a backtick inside.

See also the Python documentation about lexical analysis
([https://docs.python.org/3/reference/lexical_analysis.html](https://docs.python.org/3/reference/lexical_analysis.html))
in combination with the source code in `pandas.core.computation.parsing`.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'A': range(1, 6),
...                    'B': range(10, 0, -2),
...                    'C C': range(10, 5, -1)})
>>> df.execute()
   A   B  C C
0  1  10   10
1  2   8    9
2  3   6    8
3  4   4    7
4  5   2    6
>>> df.query('A > B').execute()
   A  B  C C
4  5  2    6
```

The previous expression is equivalent to

```pycon
>>> df[df.A > df.B].execute()
   A  B  C C
4  5  2    6
```

For columns with spaces in their name, you can use backtick quoting.

```pycon
>>> df.query('B == `C C`').execute()
   A   B  C C
0  1  10   10
```

The previous expression is equivalent to

```pycon
>>> df[df.B == df['C C']].execute()
   A   B  C C
0  1  10   10
```
