# maxframe.dataframe.Series.str.pad

#### Series.str.pad(width: [int](https://docs.python.org/3/library/functions.html#int), side: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['left', 'right', 'both'] = 'left', fillchar: [str](https://docs.python.org/3/library/stdtypes.html#str) = ' ')

Pad strings in the Series/Index up to width.

* **Parameters:**
  * **width** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Minimum width of resulting string; additional characters will be filled
    with character defined in fillchar.
  * **side** ( *{'left'* *,*  *'right'* *,*  *'both'}* *,* *default 'left'*) – Side from which to fill resulting string.
  * **fillchar** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default ' '*) – Additional character for filling, default is whitespace.
* **Returns:**
  Returns Series or Index with minimum number of char in object.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index) of [object](https://docs.python.org/3/library/functions.html#object)

#### SEE ALSO
[`Series.str.rjust`](maxframe.dataframe.Series.str.rjust.md#maxframe.dataframe.Series.str.rjust)
: Fills the left side of strings with an arbitrary character. Equivalent to `Series.str.pad(side='left')`.

[`Series.str.ljust`](maxframe.dataframe.Series.str.ljust.md#maxframe.dataframe.Series.str.ljust)
: Fills the right side of strings with an arbitrary character. Equivalent to `Series.str.pad(side='right')`.

`Series.str.center`
: Fills both sides of strings with an arbitrary character. Equivalent to `Series.str.pad(side='both')`.

[`Series.str.zfill`](maxframe.dataframe.Series.str.zfill.md#maxframe.dataframe.Series.str.zfill)
: Pad strings in the Series/Index by prepending ‘0’ character. Equivalent to `Series.str.pad(side='left', fillchar='0')`.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(["caribou", "tiger"])
>>> s.execute()
0    caribou
1      tiger
dtype: object
```

```pycon
>>> s.str.pad(width=10).execute()
0       caribou
1         tiger
dtype: object
```

```pycon
>>> s.str.pad(width=10, side='right', fillchar='-').execute()
0    caribou---
1    tiger-----
dtype: object
```

```pycon
>>> s.str.pad(width=10, side='both', fillchar='-').execute()
0    -caribou--
1    --tiger---
dtype: object
```
