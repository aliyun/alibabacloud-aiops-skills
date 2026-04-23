# maxframe.dataframe.Series.str.startswith

#### Series.str.startswith(pat: [str](https://docs.python.org/3/library/stdtypes.html#str) | [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...], na: Scalar | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) | [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

Test if the start of each string element matches a pattern.

Equivalent to [`str.startswith()`](https://docs.python.org/3/library/stdtypes.html#str.startswith).

* **Parameters:**
  * **pat** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,*  *...* *]*) – Character sequence or tuple of strings. Regular expressions are not
    accepted.
  * **na** ([*object*](https://docs.python.org/3/library/functions.html#object) *,* *default NaN*) – Object shown if element tested is not a string. The default depends
    on dtype of the array. For object-dtype, `numpy.nan` is used.
    For `StringDtype`, `pandas.NA` is used.
* **Returns:**
  A Series of booleans indicating whether the given pattern matches
  the start of each string element.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index) of [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`str.startswith`](https://docs.python.org/3/library/stdtypes.html#str.startswith)
: Python standard library string method.

[`Series.str.endswith`](maxframe.dataframe.Series.str.endswith.md#maxframe.dataframe.Series.str.endswith)
: Same as startswith, but tests the end of string.

[`Series.str.contains`](maxframe.dataframe.Series.str.contains.md#maxframe.dataframe.Series.str.contains)
: Tests if string element contains a pattern.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series(['bat', 'Bear', 'cat', mt.nan])
>>> s.execute()
0     bat
1    Bear
2     cat
3     NaN
dtype: object
```

```pycon
>>> s.str.startswith('b').execute()
0     True
1    False
2    False
3      NaN
dtype: object
```

```pycon
>>> s.str.startswith(('b', 'B')).execute()
0     True
1     True
2    False
3      NaN
dtype: object
```

Specifying na to be False instead of NaN.

```pycon
>>> s.str.startswith('b', na=False).execute()
0     True
1    False
2    False
3    False
dtype: bool
```
