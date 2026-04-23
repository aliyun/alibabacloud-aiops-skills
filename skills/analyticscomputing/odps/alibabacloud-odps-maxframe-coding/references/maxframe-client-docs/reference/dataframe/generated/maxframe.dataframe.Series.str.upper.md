# maxframe.dataframe.Series.str.upper

#### Series.str.upper()

Convert strings in the Series/Index to uppercase.

Equivalent to [`str.upper()`](https://docs.python.org/3/library/stdtypes.html#str.upper).

* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index) of [object](https://docs.python.org/3/library/functions.html#object)

#### SEE ALSO
[`Series.str.lower`](maxframe.dataframe.Series.str.lower.md#maxframe.dataframe.Series.str.lower)
: Converts all characters to lowercase.

[`Series.str.upper`](#maxframe.dataframe.Series.str.upper)
: Converts all characters to uppercase.

[`Series.str.title`](maxframe.dataframe.Series.str.title.md#maxframe.dataframe.Series.str.title)
: Converts first character of each word to uppercase and remaining to lowercase.

[`Series.str.capitalize`](maxframe.dataframe.Series.str.capitalize.md#maxframe.dataframe.Series.str.capitalize)
: Converts first character to uppercase and remaining to lowercase.

[`Series.str.swapcase`](maxframe.dataframe.Series.str.swapcase.md#maxframe.dataframe.Series.str.swapcase)
: Converts uppercase to lowercase and lowercase to uppercase.

`Series.str.casefold`
: Removes all case distinctions in the string.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(['lower', 'CAPITALS', 'this is a sentence', 'SwApCaSe'])
>>> s.execute()
0                 lower
1              CAPITALS
2    this is a sentence
3              SwApCaSe
dtype: object
```

```pycon
>>> s.str.lower().execute()
0                 lower
1              capitals
2    this is a sentence
3              swapcase
dtype: object
```

```pycon
>>> s.str.upper().execute()
0                 LOWER
1              CAPITALS
2    THIS IS A SENTENCE
3              SWAPCASE
dtype: object
```

```pycon
>>> s.str.title().execute()
0                 Lower
1              Capitals
2    This Is A Sentence
3              Swapcase
dtype: object
```

```pycon
>>> s.str.capitalize().execute()
0                 Lower
1              Capitals
2    This is a sentence
3              Swapcase
dtype: object
```

```pycon
>>> s.str.swapcase().execute()
0                 LOWER
1              capitals
2    THIS IS A SENTENCE
3              sWaPcAsE
dtype: object
```
