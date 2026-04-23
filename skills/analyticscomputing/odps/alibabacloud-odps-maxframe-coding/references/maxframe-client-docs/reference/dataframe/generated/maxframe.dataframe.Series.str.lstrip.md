# maxframe.dataframe.Series.str.lstrip

#### Series.str.lstrip(to_strip=None)

Remove leading characters.

Strip whitespaces (including newlines) or a set of specified characters
from each string in the Series/Index from left side.
Replaces any non-strings in Series with NaNs.
Equivalent to [`str.lstrip()`](https://docs.python.org/3/library/stdtypes.html#str.lstrip).

* **Parameters:**
  **to_strip** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *None* *,* *default None*) – Specifying the set of characters to be removed.
  All combinations of this set of characters will be stripped.
  If None then whitespaces are removed.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index) of [object](https://docs.python.org/3/library/functions.html#object)

#### SEE ALSO
[`Series.str.strip`](maxframe.dataframe.Series.str.strip.md#maxframe.dataframe.Series.str.strip)
: Remove leading and trailing characters in Series/Index.

[`Series.str.lstrip`](#maxframe.dataframe.Series.str.lstrip)
: Remove leading characters in Series/Index.

[`Series.str.rstrip`](maxframe.dataframe.Series.str.rstrip.md#maxframe.dataframe.Series.str.rstrip)
: Remove trailing characters in Series/Index.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series(['1. Ant.  ', '2. Bee!\n', '3. Cat?\t', mt.nan, 10, True])
>>> s.execute()
0    1. Ant.
1    2. Bee!\n
2    3. Cat?\t
3          NaN
4           10
5         True
dtype: object
```

```pycon
>>> s.str.strip().execute()
0    1. Ant.
1    2. Bee!
2    3. Cat?
3        NaN
4        NaN
5        NaN
dtype: object
```

```pycon
>>> s.str.lstrip('123.').execute()
0    Ant.
1    Bee!\n
2    Cat?\t
3       NaN
4       NaN
5       NaN
dtype: object
```

```pycon
>>> s.str.rstrip('.!? \n\t').execute()
0    1. Ant
1    2. Bee
2    3. Cat
3       NaN
4       NaN
5       NaN
dtype: object
```

```pycon
>>> s.str.strip('123.!? \n\t').execute()
0    Ant
1    Bee
2    Cat
3    NaN
4    NaN
5    NaN
dtype: object
```
