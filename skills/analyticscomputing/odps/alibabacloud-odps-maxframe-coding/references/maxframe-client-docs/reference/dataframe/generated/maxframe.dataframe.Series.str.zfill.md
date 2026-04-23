# maxframe.dataframe.Series.str.zfill

#### Series.str.zfill(width: [int](https://docs.python.org/3/library/functions.html#int))

Pad strings in the Series/Index by prepending ‘0’ characters.

Strings in the Series/Index are padded with ‘0’ characters on the
left of the string to reach a total string length  width. Strings
in the Series/Index with length greater or equal to width are
unchanged.

* **Parameters:**
  **width** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Minimum length of resulting string; strings with length less
  than width be prepended with ‘0’ characters.
* **Return type:**
  Series/Index of objects.

#### SEE ALSO
[`Series.str.rjust`](maxframe.dataframe.Series.str.rjust.md#maxframe.dataframe.Series.str.rjust)
: Fills the left side of strings with an arbitrary character.

[`Series.str.ljust`](maxframe.dataframe.Series.str.ljust.md#maxframe.dataframe.Series.str.ljust)
: Fills the right side of strings with an arbitrary character.

[`Series.str.pad`](maxframe.dataframe.Series.str.pad.md#maxframe.dataframe.Series.str.pad)
: Fills the specified sides of strings with an arbitrary character.

`Series.str.center`
: Fills both sides of strings with an arbitrary character.

### Notes

Differs from [`str.zfill()`](https://docs.python.org/3/library/stdtypes.html#str.zfill) which has special handling
for ‘+’/’-’ in the string.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series(['-1', '1', '1000', 10, mt.nan])
>>> s.execute()
0      -1
1       1
2    1000
3      10
4     NaN
dtype: object
```

Note that `10` and `NaN` are not strings, therefore they are
converted to `NaN`. The minus sign in `'-1'` is treated as a
special character and the zero is added to the right of it
([`str.zfill()`](https://docs.python.org/3/library/stdtypes.html#str.zfill) would have moved it to the left). `1000`
remains unchanged as it is longer than width.

```pycon
>>> s.str.zfill(3).execute()
0     -01
1     001
2    1000
3     NaN
4     NaN
dtype: object
```
