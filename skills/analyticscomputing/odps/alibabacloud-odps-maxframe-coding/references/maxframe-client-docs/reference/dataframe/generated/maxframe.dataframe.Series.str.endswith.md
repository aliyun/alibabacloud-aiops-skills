# maxframe.dataframe.Series.str.endswith

#### Series.str.endswith(pat: [str](https://docs.python.org/3/library/stdtypes.html#str) | [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...], na: Scalar | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) | [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

Test if the end of each string element matches a pattern.

Equivalent to [`str.endswith()`](https://docs.python.org/3/library/stdtypes.html#str.endswith).

* **Parameters:**
  * **pat** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,*  *...* *]*) – Character sequence or tuple of strings. Regular expressions are not
    accepted.
  * **na** ([*object*](https://docs.python.org/3/library/functions.html#object) *,* *default NaN*) – Object shown if element tested is not a string. The default depends
    on dtype of the array. For object-dtype, `numpy.nan` is used.
    For `StringDtype`, `pandas.NA` is used.
* **Returns:**
  A Series of booleans indicating whether the given pattern matches
  the end of each string element.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index) of [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`str.endswith`](https://docs.python.org/3/library/stdtypes.html#str.endswith)
: Python standard library string method.

[`Series.str.startswith`](maxframe.dataframe.Series.str.startswith.md#maxframe.dataframe.Series.str.startswith)
: Same as endswith, but tests the start of string.

[`Series.str.contains`](maxframe.dataframe.Series.str.contains.md#maxframe.dataframe.Series.str.contains)
: Tests if string element contains a pattern.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series(['bat', 'bear', 'caT', mt.nan])
>>> s.execute()
0     bat
1    bear
2     caT
3     NaN
dtype: object
```

```pycon
>>> s.str.endswith('t').execute()
0     True
1    False
2    False
3      NaN
dtype: object
```

```pycon
>>> s.str.endswith(('t', 'T')).execute()
0     True
1    False
2     True
3      NaN
dtype: object
```

Specifying na to be False instead of NaN.

```pycon
>>> s.str.endswith('t', na=False).execute()
0     True
1    False
2    False
3    False
dtype: bool
```
