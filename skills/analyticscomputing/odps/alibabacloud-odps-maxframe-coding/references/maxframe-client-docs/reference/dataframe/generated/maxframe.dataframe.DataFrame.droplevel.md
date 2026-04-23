# maxframe.dataframe.DataFrame.droplevel

#### DataFrame.droplevel(level, axis=0)

Return Series/DataFrame with requested index / column level(s) removed.

* **Parameters:**
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *, or* *list-like*) – If a string is given, must be the name of a level
    If list-like, elements must be names or positional indexes
    of levels.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – 

    Axis along which the level(s) is removed:
    * 0 or ‘index’: remove level(s) in column.
    * 1 or ‘columns’: remove level(s) in row.

    For Series this parameter is unused and defaults to 0.
* **Returns:**
  Series/DataFrame with requested index / column level(s) removed.
* **Return type:**
  Series/DataFrame

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([
...     [1, 2, 3, 4],
...     [5, 6, 7, 8],
...     [9, 10, 11, 12]
... ]).set_index([0, 1]).rename_axis(['a', 'b'])
```

```pycon
>>> df.columns = md.MultiIndex.from_tuples([
...     ('c', 'e'), ('d', 'f')
... ], names=['level_1', 'level_2'])
```

```pycon
>>> df.execute()
level_1   c   d
level_2   e   f
a b
1 2      3   4
5 6      7   8
9 10    11  12
```

```pycon
>>> df.droplevel('a').execute()
level_1   c   d
level_2   e   f
b
2        3   4
6        7   8
10      11  12
```

```pycon
>>> df.droplevel('level_2', axis=1).execute()
level_1   c   d
a b
1 2      3   4
5 6      7   8
9 10    11  12
```
