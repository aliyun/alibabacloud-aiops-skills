# maxframe.dataframe.Series.update

#### Series.update(other)

Modify Series in place using values from passed Series.

Uses non-NA values from passed Series to make updates. Aligns
on index.

* **Parameters:**
  **other** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *, or* *object coercible into Series*)

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series([1, 2, 3])
>>> s.update(md.Series([4, 5, 6]))
>>> s.execute()
0    4
1    5
2    6
dtype: int64
```

```pycon
>>> s = md.Series(['a', 'b', 'c'])
>>> s.update(md.Series(['d', 'e'], index=[0, 2]))
>>> s.execute()
0    d
1    b
2    e
dtype: object
```

```pycon
>>> s = md.Series([1, 2, 3])
>>> s.update(md.Series([4, 5, 6, 7, 8]))
>>> s.execute()
0    4
1    5
2    6
dtype: int64
```

If `other` contains NaNs the corresponding values are not updated
in the original Series.

```pycon
>>> s = md.Series([1, 2, 3])
>>> s.update(md.Series([4, mt.nan, 6]))
>>> s.execute()
0    4
1    2
2    6
dtype: int64
```

`other` can also be a non-Series object type
that is coercible into a Series

```pycon
>>> s = md.Series([1, 2, 3])
>>> s.update([4, mt.nan, 6])
>>> s.execute()
0    4
1    2
2    6
dtype: int64
```

```pycon
>>> s = md.Series([1, 2, 3])
>>> s.update({1: 9})
>>> s.execute()
0    1
1    9
2    3
dtype: int64
```
