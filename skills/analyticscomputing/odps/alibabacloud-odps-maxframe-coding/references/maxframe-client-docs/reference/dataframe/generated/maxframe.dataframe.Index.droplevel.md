# maxframe.dataframe.Index.droplevel

#### Index.droplevel(level)

Return index with requested level(s) removed.

If resulting index has only 1 level left, the result will be
of Index type, not MultiIndex. The original index is not modified inplace.

* **Parameters:**
  **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *, or* *list-like* *,* *default 0*) – If a string is given, must be the name of a level
  If list-like, elements must be names or indexes of levels.
* **Return type:**
  [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index) or MultiIndex

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> mi = md.MultiIndex.from_arrays(
... [[1, 2], [3, 4], [5, 6]], names=['x', 'y', 'z'])
>>> mi.execute()
MultiIndex([(1, 3, 5),
            (2, 4, 6)],
            names=['x', 'y', 'z'])
```

```pycon
>>> mi.droplevel().execute()
MultiIndex([(3, 5),
            (4, 6)],
            names=['y', 'z'])
```

```pycon
>>> mi.droplevel(2).execute()
MultiIndex([(1, 3),
            (2, 4)],
            names=['x', 'y'])
```

```pycon
>>> mi.droplevel('z').execute()
MultiIndex([(1, 3),
            (2, 4)],
            names=['x', 'y'])
```

```pycon
>>> mi.droplevel(['x', 'y']).execute()
Index([5, 6], dtype='int64', name='z')
```
