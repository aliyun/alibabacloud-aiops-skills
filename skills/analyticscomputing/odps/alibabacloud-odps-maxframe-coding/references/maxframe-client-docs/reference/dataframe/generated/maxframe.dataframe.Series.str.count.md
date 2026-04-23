# maxframe.dataframe.Series.str.count

#### Series.str.count(pat, flags: [int](https://docs.python.org/3/library/functions.html#int) = 0)

Count occurrences of pattern in each string of the Series/Index.

This function is used to count the number of times a particular regex
pattern is repeated in each of the string elements of the
[`Series`](https://pandas.pydata.org/docs/reference/api/pandas.Series.html#pandas.Series).

* **Parameters:**
  * **pat** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Valid regular expression.
  * **flags** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 0* *,* *meaning no flags*) – Flags for the re module. For a complete list, [see here](https://docs.python.org/3/howto/regex.html#compilation-flags).
  * **\*\*kwargs** – For compatibility with other string methods. Not used.
* **Returns:**
  Same type as the calling object containing the integer counts.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

#### SEE ALSO
[`re`](https://docs.python.org/3/library/re.html#module-re)
: Standard library module for regular expressions.

[`str.count`](https://docs.python.org/3/library/stdtypes.html#str.count)
: Standard library version, without regular expression support.

### Notes

Some characters need to be escaped when passing in pat.
eg. `'$'` has a special meaning in regex and must be escaped when
finding this literal character.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series(['A', 'B', 'Aaba', 'Baca', mt.nan, 'CABA', 'cat'])
>>> s.str.count('a').execute()
0    0.0
1    0.0
2    2.0
3    2.0
4    NaN
5    0.0
6    1.0
dtype: float64
```

Escape `'$'` to find the literal dollar sign.

```pycon
>>> s = md.Series(['$', 'B', 'Aab$', '$$ca', 'C$B$', 'cat'])
>>> s.str.count('\\$').execute()
0    1
1    0
2    1
3    2
4    2
5    0
dtype: int64
```

This is also available on Index

```pycon
>>> md.Index(['A', 'A', 'Aaba', 'cat']).str.count('a').execute()
Index([0, 0, 2, 1], dtype='int64')
```
