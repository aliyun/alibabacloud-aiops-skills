# maxframe.dataframe.DataFrame.mask

#### DataFrame.mask(cond, other=nan, inplace=False, axis=None, level=None, errors='raise', try_cast=False)

Replace values where the condition is True.

* **Parameters:**
  * **cond** (*bool Series/DataFrame* *,* *array-like* *, or* *callable*) – Where cond is False, keep the original value. Where
    True, replace with corresponding value from other.
    If cond is callable, it is computed on the Series/DataFrame and
    should return boolean Series/DataFrame or array. The callable must
    not change input Series/DataFrame (though pandas doesn’t check it).
  * **other** (*scalar* *,* *Series/DataFrame* *, or* *callable*) – Entries where cond is True are replaced with
    corresponding value from other.
    If other is callable, it is computed on the Series/DataFrame and
    should return scalar or Series/DataFrame. The callable must not
    change input Series/DataFrame (though pandas doesn’t check it).
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether to perform the operation in place on the data.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default None*) – Alignment axis if needed.
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default None*) – Alignment level if needed.
* **Return type:**
  Same type as caller

#### SEE ALSO
[`DataFrame.where()`](maxframe.dataframe.DataFrame.where.md#maxframe.dataframe.DataFrame.where)
: Return an object of same shape as self.

### Notes

The mask method is an application of the if-then idiom. For each
element in the calling DataFrame, if `cond` is `False` the
element is used; otherwise the corresponding element from the DataFrame
`other` is used.

The signature for [`DataFrame.where()`](maxframe.dataframe.DataFrame.where.md#maxframe.dataframe.DataFrame.where) differs from
[`numpy.where()`](https://numpy.org/doc/stable/reference/generated/numpy.where.html#numpy.where). Roughly `df1.where(m, df2)` is equivalent to
`np.where(m, df1, df2)`.

For further details and examples see the `mask` documentation in
[indexing](https://pandas.pydata.org/docs/user_guide/indexing.html#indexing-where-mask).

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series(range(5))
>>> s.where(s > 0).execute()
0    NaN
1    1.0
2    2.0
3    3.0
4    4.0
dtype: float64
```

```pycon
>>> s.mask(s > 0).execute()
0    0.0
1    NaN
2    NaN
3    NaN
4    NaN
dtype: float64
```

```pycon
>>> s.where(s > 1, 10).execute()
0    10
1    10
2    2
3    3
4    4
dtype: int64
```

```pycon
>>> df = md.DataFrame(mt.arange(10).reshape(-1, 2), columns=['A', 'B'])
>>> df.execute()
   A  B
0  0  1
1  2  3
2  4  5
3  6  7
4  8  9
>>> m = df % 3 == 0
>>> df.where(m, -df).execute()
   A  B
0  0 -1
1 -2  3
2 -4 -5
3  6 -7
4 -8  9
>>> df.where(m, -df) == mt.where(m, df, -df).execute()
      A     B
0  True  True
1  True  True
2  True  True
3  True  True
4  True  True
>>> df.where(m, -df) == df.mask(~m, -df).execute()
      A     B
0  True  True
1  True  True
2  True  True
3  True  True
4  True  True
```
