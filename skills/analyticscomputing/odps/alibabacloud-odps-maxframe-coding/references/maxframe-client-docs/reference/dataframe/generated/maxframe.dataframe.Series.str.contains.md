# maxframe.dataframe.Series.str.contains

#### Series.str.contains(pat, case: [bool](https://docs.python.org/3/library/functions.html#bool) = True, flags: [int](https://docs.python.org/3/library/functions.html#int) = 0, na=None, regex: [bool](https://docs.python.org/3/library/functions.html#bool) = True)

Test if pattern or regex is contained within a string of a Series or Index.

Return boolean Series or Index based on whether a given pattern or regex is
contained within a string of a Series or Index.

* **Parameters:**
  * **pat** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Character sequence or regular expression.
  * **case** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If True, case sensitive.
  * **flags** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 0* *(**no flags* *)*) – Flags to pass through to the re module, e.g. re.IGNORECASE.
  * **na** (*scalar* *,* *optional*) – Fill value for missing values. The default depends on dtype of the
    array. For object-dtype, `numpy.nan` is used. For `StringDtype`,
    `pandas.NA` is used.
  * **regex** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – 

    If True, assumes the pat is a regular expression.

    If False, treats the pat as a literal string.
* **Returns:**
  A Series or Index of boolean values indicating whether the
  given pattern is contained within the string of each element
  of the Series or Index.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index) of boolean values

#### SEE ALSO
`match`
: Analogous, but stricter, relying on re.match instead of re.search.

[`Series.str.startswith`](maxframe.dataframe.Series.str.startswith.md#maxframe.dataframe.Series.str.startswith)
: Test if the start of each string element matches a pattern.

[`Series.str.endswith`](maxframe.dataframe.Series.str.endswith.md#maxframe.dataframe.Series.str.endswith)
: Same as startswith, but tests the end of string.

### Examples

Returning a Series of booleans using only a literal pattern.

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s1 = md.Series(['Mouse', 'dog', 'house and parrot', '23', mt.nan])
>>> s1.str.contains('og', regex=False).execute()
0    False
1     True
2    False
3    False
4      NaN
dtype: object
```

Returning an Index of booleans using only a literal pattern.

```pycon
>>> ind = md.Index(['Mouse', 'dog', 'house and parrot', '23.0', mt.nan])
>>> ind.str.contains('23', regex=False).execute()
Index([False, False, False, True, nan], dtype='object')
```

Specifying case sensitivity using case.

```pycon
>>> s1.str.contains('oG', case=True, regex=True).execute()
0    False
1    False
2    False
3    False
4      NaN
dtype: object
```

Specifying na to be False instead of NaN replaces NaN values
with False. If Series or Index does not contain NaN values
the resultant dtype will be bool, otherwise, an object dtype.

```pycon
>>> s1.str.contains('og', na=False, regex=True).execute()
0    False
1     True
2    False
3    False
4    False
dtype: bool
```

Returning ‘house’ or ‘dog’ when either expression occurs in a string.

```pycon
>>> s1.str.contains('house|dog', regex=True).execute()
0    False
1     True
2     True
3    False
4      NaN
dtype: object
```

Ignoring case sensitivity using flags with regex.

```pycon
>>> import re
>>> s1.str.contains('PARROT', flags=re.IGNORECASE, regex=True).execute()
0    False
1    False
2     True
3    False
4      NaN
dtype: object
```

Returning any digit using regular expression.

```pycon
>>> s1.str.contains('\\d', regex=True).execute()
0    False
1    False
2    False
3     True
4      NaN
dtype: object
```

Ensure pat is a not a literal pattern when regex is set to True.
Note in the following example one might expect only s2[1] and s2[3] to
return True. However, ‘.0’ as a regex matches any character
followed by a 0.

```pycon
>>> s2 = md.Series(['40', '40.0', '41', '41.0', '35'])
>>> s2.str.contains('.0', regex=True).execute()
0     True
1     True
2    False
3     True
4    False
dtype: bool
```
