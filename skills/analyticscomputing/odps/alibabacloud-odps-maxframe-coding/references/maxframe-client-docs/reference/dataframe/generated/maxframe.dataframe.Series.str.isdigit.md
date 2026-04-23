# maxframe.dataframe.Series.str.isdigit

#### Series.str.isdigit()

Check whether all characters in each string are digits.

This is equivalent to running the Python string method
[`str.isdigit()`](https://docs.python.org/3/library/stdtypes.html#str.isdigit) for each element of the Series/Index. If a string
has zero characters, `False` is returned for that check.

* **Returns:**
  Series or Index of boolean values with the same length as the original
  Series/Index.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index) of [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`Series.str.isalpha`](maxframe.dataframe.Series.str.isalpha.md#maxframe.dataframe.Series.str.isalpha)
: Check whether all characters are alphabetic.

[`Series.str.isnumeric`](maxframe.dataframe.Series.str.isnumeric.md#maxframe.dataframe.Series.str.isnumeric)
: Check whether all characters are numeric.

[`Series.str.isalnum`](maxframe.dataframe.Series.str.isalnum.md#maxframe.dataframe.Series.str.isalnum)
: Check whether all characters are alphanumeric.

[`Series.str.isdigit`](#maxframe.dataframe.Series.str.isdigit)
: Check whether all characters are digits.

[`Series.str.isdecimal`](maxframe.dataframe.Series.str.isdecimal.md#maxframe.dataframe.Series.str.isdecimal)
: Check whether all characters are decimal.

[`Series.str.isspace`](maxframe.dataframe.Series.str.isspace.md#maxframe.dataframe.Series.str.isspace)
: Check whether all characters are whitespace.

[`Series.str.islower`](maxframe.dataframe.Series.str.islower.md#maxframe.dataframe.Series.str.islower)
: Check whether all characters are lowercase.

[`Series.str.isupper`](maxframe.dataframe.Series.str.isupper.md#maxframe.dataframe.Series.str.isupper)
: Check whether all characters are uppercase.

[`Series.str.istitle`](maxframe.dataframe.Series.str.istitle.md#maxframe.dataframe.Series.str.istitle)
: Check whether all characters are titlecase.

### Examples

**Checks for Alphabetic and Numeric Characters**

```pycon
>>> import maxframe.dataframe as md
>>> s1 = md.Series(['one', 'one1', '1', ''])
```

```pycon
>>> s1.str.isalpha().execute()
0     True
1    False
2    False
3    False
dtype: bool
```

```pycon
>>> s1.str.isnumeric().execute()
0    False
1    False
2     True
3    False
dtype: bool
```

```pycon
>>> s1.str.isalnum().execute()
0     True
1     True
2     True
3    False
dtype: bool
```

Note that checks against characters mixed with any additional punctuation
or whitespace will evaluate to false for an alphanumeric check.

```pycon
>>> s2 = md.Series(['A B', '1.5', '3,000'])
>>> s2.str.isalnum().execute()
0    False
1    False
2    False
dtype: bool
```

**More Detailed Checks for Numeric Characters**

There are several different but overlapping sets of numeric characters that
can be checked for.

```pycon
>>> s3 = md.Series(['23', '³', '⅕', ''])
```

The `s3.str.isdecimal` method checks for characters used to form numbers
in base 10.

```pycon
>>> s3.str.isdecimal().execute()
0     True
1    False
2    False
3    False
dtype: bool
```

The `s.str.isdigit` method is the same as `s3.str.isdecimal` but also
includes special digits, like superscripted and subscripted digits in
unicode.

```pycon
>>> s3.str.isdigit().execute()
0     True
1     True
2    False
3    False
dtype: bool
```

The `s.str.isnumeric` method is the same as `s3.str.isdigit` but also
includes other characters that can represent quantities such as unicode
fractions.

```pycon
>>> s3.str.isnumeric().execute()
0     True
1     True
2     True
3    False
dtype: bool
```

**Checks for Whitespace**

```pycon
>>> s4 = md.Series([' ', '\t\r\n ', ''])
>>> s4.str.isspace().execute()
0     True
1     True
2    False
dtype: bool
```

**Checks for Character Case**

```pycon
>>> s5 = md.Series(['leopard', 'Golden Eagle', 'SNAKE', ''])
```

```pycon
>>> s5.str.islower().execute()
0     True
1    False
2    False
3    False
dtype: bool
```

```pycon
>>> s5.str.isupper().execute()
0    False
1    False
2     True
3    False
dtype: bool
```

The `s5.str.istitle` method checks for whether all words are in title
case (whether only the first letter of each word is capitalized). Words are
assumed to be as any sequence of non-numeric characters separated by
whitespace characters.

```pycon
>>> s5.str.istitle().execute()
0    False
1     True
2    False
3    False
dtype: bool
```
