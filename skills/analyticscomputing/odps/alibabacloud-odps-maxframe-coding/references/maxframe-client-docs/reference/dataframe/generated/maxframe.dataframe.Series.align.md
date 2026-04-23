# maxframe.dataframe.Series.align

#### Series.align(other, join: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'outer', axis: [int](https://docs.python.org/3/library/functions.html#int) | [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, level: [int](https://docs.python.org/3/library/functions.html#int) | [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, copy: [bool](https://docs.python.org/3/library/functions.html#bool) = True, fill_value: [Any](https://docs.python.org/3/library/typing.html#typing.Any) = None, method: [str](https://docs.python.org/3/library/stdtypes.html#str) = None, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, fill_axis: [int](https://docs.python.org/3/library/functions.html#int) | [str](https://docs.python.org/3/library/stdtypes.html#str) = 0, broadcast_axis: [int](https://docs.python.org/3/library/functions.html#int) | [str](https://docs.python.org/3/library/stdtypes.html#str) = None)

Align two objects on their axes with the specified join method.

Join method is specified for each axis Index.

* **Parameters:**
  * **other** ([*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) *or* [*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series))
  * **join** ( *{'outer'* *,*  *'inner'* *,*  *'left'* *,*  *'right'}* *,* *default 'outer'*)
  * **axis** (*allowed axis* *of* *the other object* *,* *default None*) – Align on index (0), columns (1), or both (None).
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *level name* *,* *default None*) – Broadcast across a level, matching Index values on the
    passed MultiIndex level.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Always returns new objects. If copy=False and no reindexing is
    required then original objects are returned.
  * **fill_value** (*scalar* *,* *default np.NaN*) – Value to use for missing values. Defaults to NaN, but can be any
    “compatible” value.
  * **method** ( *{'backfill'* *,*  *'bfill'* *,*  *'pad'* *,*  *'ffill'* *,* *None}* *,* *default None*) – 

    Method to use for filling holes in reindexed Series:
    - pad / ffill: propagate last valid observation forward to next valid.
    - backfill / bfill: use NEXT valid observation to fill gap.
  * **limit** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default None*) – If method is specified, this is the maximum number of consecutive
    NaN values to forward/backward fill. In other words, if there is
    a gap with more than this number of consecutive NaNs, it will only
    be partially filled. If method is not specified, this is the
    maximum number of entries along the entire axis where NaNs will be
    filled. Must be greater than 0 if not None.
  * **fill_axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – Filling axis, method and limit.
  * **broadcast_axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default None*) – Broadcast values along this axis, if aligning two objects of
    different dimensions.

### Notes

Currently argument level is not supported.

* **Returns:**
  **(left, right)** – Aligned objects.
* **Return type:**
  ([DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame), [type](https://docs.python.org/3/library/functions.html#type) of other)

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame(
...     [[1, 2, 3, 4], [6, 7, 8, 9]], columns=["D", "B", "E", "A"], index=[1, 2]
... )
>>> other = md.DataFrame(
...     [[10, 20, 30, 40], [60, 70, 80, 90], [600, 700, 800, 900]],
...     columns=["A", "B", "C", "D"],
...     index=[2, 3, 4],
... )
>>> df.execute()
   D  B  E  A
1  1  2  3  4
2  6  7  8  9
>>> other.execute()
    A    B    C    D
2   10   20   30   40
3   60   70   80   90
4  600  700  800  900
```

Align on columns:

```pycon
>>> left, right = df.align(other, join="outer", axis=1)
>>> left.execute()
   A  B   C  D  E
1  4  2 NaN  1  3
2  9  7 NaN  6  8
>>> right.execute()
    A    B    C    D   E
2   10   20   30   40 NaN
3   60   70   80   90 NaN
4  600  700  800  900 NaN
```

We can also align on the index:

```pycon
>>> left, right = df.align(other, join="outer", axis=0)
>>> left.execute()
    D    B    E    A
1  1.0  2.0  3.0  4.0
2  6.0  7.0  8.0  9.0
3  NaN  NaN  NaN  NaN
4  NaN  NaN  NaN  NaN
>>> right.execute()
    A      B      C      D
1    NaN    NaN    NaN    NaN
2   10.0   20.0   30.0   40.0
3   60.0   70.0   80.0   90.0
4  600.0  700.0  800.0  900.0
```

Finally, the default axis=None will align on both index and columns:

```pycon
>>> left, right = df.align(other, join="outer", axis=None)
>>> left.execute()
     A    B   C    D    E
1  4.0  2.0 NaN  1.0  3.0
2  9.0  7.0 NaN  6.0  8.0
3  NaN  NaN NaN  NaN  NaN
4  NaN  NaN NaN  NaN  NaN
>>> right.execute()
       A      B      C      D   E
1    NaN    NaN    NaN    NaN NaN
2   10.0   20.0   30.0   40.0 NaN
3   60.0   70.0   80.0   90.0 NaN
4  600.0  700.0  800.0  900.0 NaN
```
