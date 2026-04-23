# maxframe.dataframe.DataFrame.pivot

#### DataFrame.pivot(columns, index=None, values=None)

Return reshaped DataFrame organized by given index / column values.

Reshape data (produce a “pivot” table) based on column values. Uses
unique values from specified index / columns to form axes of the
resulting DataFrame. This function does not support data
aggregation, multiple values will result in a MultiIndex in the
columns. See the [User Guide](https://pandas.pydata.org/docs/user_guide/reshaping.html#reshaping) for more on reshaping.

* **Parameters:**
  * **index** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*object*](https://docs.python.org/3/library/functions.html#object) *or* *a list* *of* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Column to use to make new frame’s index. If None, uses
    existing index.
  * **columns** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*object*](https://docs.python.org/3/library/functions.html#object) *or* *a list* *of* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Column to use to make new frame’s columns.
  * **values** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*object*](https://docs.python.org/3/library/functions.html#object) *or* *a list* *of* *the previous* *,* *optional*) – Column(s) to use for populating new frame’s values. If not
    specified, all remaining columns will be used and the result will
    have hierarchically indexed columns.
* **Returns:**
  Returns reshaped DataFrame.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
* **Raises:**
  **ValueError:** – When there are any index, columns combinations with multiple
      values. DataFrame.pivot_table when you need to aggregate.

#### SEE ALSO
[`DataFrame.pivot_table`](maxframe.dataframe.DataFrame.pivot_table.md#maxframe.dataframe.DataFrame.pivot_table)
: Generalization of pivot that can handle duplicate values for one index/column pair.

[`DataFrame.unstack`](maxframe.dataframe.DataFrame.unstack.md#maxframe.dataframe.DataFrame.unstack)
: Pivot based on the index values instead of a column.

`wide_to_long`
: Wide panel to long format. Less flexible but more user-friendly than melt.

### Notes

For finer-tuned control, see hierarchical indexing documentation along
with the related stack/unstack methods.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'foo': ['one', 'one', 'one', 'two', 'two',
...                            'two'],
...                    'bar': ['A', 'B', 'C', 'A', 'B', 'C'],
...                    'baz': [1, 2, 3, 4, 5, 6],
...                    'zoo': ['x', 'y', 'z', 'q', 'w', 't']})
>>> df.execute()
    foo   bar  baz  zoo
0   one   A    1    x
1   one   B    2    y
2   one   C    3    z
3   two   A    4    q
4   two   B    5    w
5   two   C    6    t
```

```pycon
>>> df.pivot(index='foo', columns='bar', values='baz').execute()
bar  A   B   C
foo
one  1   2   3
two  4   5   6
```

```pycon
>>> df.pivot(index='foo', columns='bar', values=['baz', 'zoo']).execute()
      baz       zoo
bar   A  B  C   A  B  C
foo
one   1  2  3   x  y  z
two   4  5  6   q  w  t
```

You could also assign a list of column names or a list of index names.

```pycon
>>> df = md.DataFrame({
...        "lev1": [1, 1, 1, 2, 2, 2],
...        "lev2": [1, 1, 2, 1, 1, 2],
...        "lev3": [1, 2, 1, 2, 1, 2],
...        "lev4": [1, 2, 3, 4, 5, 6],
...        "values": [0, 1, 2, 3, 4, 5]})
>>> df.execute()
    lev1 lev2 lev3 lev4 values
0   1    1    1    1    0
1   1    1    2    2    1
2   1    2    1    3    2
3   2    1    2    4    3
4   2    1    1    5    4
5   2    2    2    6    5
```

```pycon
>>> df.pivot(index="lev1", columns=["lev2", "lev3"], values="values").execute()
lev2    1         2
lev3    1    2    1    2
lev1
1     0.0  1.0  2.0  NaN
2     4.0  3.0  NaN  5.0
```

```pycon
>>> df.pivot(index=["lev1", "lev2"], columns=["lev3"], values="values").execute()
      lev3    1    2
lev1  lev2
   1     1  0.0  1.0
         2  2.0  NaN
   2     1  4.0  3.0
         2  NaN  5.0
```

A ValueError is raised if there are any duplicates.

```pycon
>>> df = md.DataFrame({"foo": ['one', 'one', 'two', 'two'],
...                    "bar": ['A', 'A', 'B', 'C'],
...                    "baz": [1, 2, 3, 4]})
>>> df.execute()
   foo bar  baz
0  one   A    1
1  one   A    2
2  two   B    3
3  two   C    4
```

Notice that the first two rows are the same for our index
and columns arguments.

```pycon
>>> df.pivot(index='foo', columns='bar', values='baz').execute()
Traceback (most recent call last):
   ...
ValueError: Index contains duplicate entries, cannot reshape
```
