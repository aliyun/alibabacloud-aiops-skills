# maxframe.dataframe.Series.unstack

#### Series.unstack(level=-1, fill_value=None)

Unstack, also known as pivot, Series with MultiIndex to produce DataFrame.

* **Parameters:**
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *, or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *these* *,* *default last level*) – Level(s) to unstack, can pass level name.
  * **fill_value** (*scalar value* *,* *default None*) – Value to use when replacing NaN values.
* **Returns:**
  Unstacked Series.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series([1, 2, 3, 4],
...               index=md.MultiIndex.from_product([['one', 'two'],
...                                                 ['a', 'b']]))
>>> s.execute()
one  a    1
     b    2
two  a    3
     b    4
dtype: int64
```

```pycon
>>> s.unstack(level=-1).execute()
     a  b
one  1  2
two  3  4
```

```pycon
>>> s.unstack(level=0).execute()
     one  two
a    1    3
b    2    4
```
