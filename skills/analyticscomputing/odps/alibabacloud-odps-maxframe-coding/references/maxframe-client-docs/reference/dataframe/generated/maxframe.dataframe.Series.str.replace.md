# maxframe.dataframe.Series.str.replace

#### Series.str.replace(pat: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Pattern](https://docs.python.org/3/library/re.html#re.Pattern), repl: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Callable](https://docs.python.org/3/library/typing.html#typing.Callable), n: [int](https://docs.python.org/3/library/functions.html#int) = -1, case: [bool](https://docs.python.org/3/library/functions.html#bool) | [None](https://docs.python.org/3/library/constants.html#None) = None, flags: [int](https://docs.python.org/3/library/functions.html#int) = 0, regex: [bool](https://docs.python.org/3/library/functions.html#bool) = False)

Replace each occurrence of pattern/regex in the Series/Index.

Equivalent to [`str.replace()`](https://docs.python.org/3/library/stdtypes.html#str.replace) or [`re.sub()`](https://docs.python.org/3/library/re.html#re.sub), depending on
the regex value.

* **Parameters:**
  * **pat** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *compiled regex*) – String can be a character sequence or regular expression.
  * **repl** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *callable*) – Replacement string or a callable. The callable is passed the regex
    match object and must return a replacement string to be used.
    See [`re.sub()`](https://docs.python.org/3/library/re.html#re.sub).
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default -1* *(**all* *)*) – Number of replacements to make from start.
  * **case** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default None*) – 

    Determines if replace is case sensitive:
    - If True, case sensitive (the default if pat is a string)
    - Set to False for case insensitive
    - Cannot be set if pat is a compiled regex.
  * **flags** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 0* *(**no flags* *)*) – Regex module flags, e.g. re.IGNORECASE. Cannot be set if pat is a compiled
    regex.
  * **regex** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – 

    Determines if the passed-in pattern is a regular expression:
    - If True, assumes the passed-in pattern is a regular expression.
    - If False, treats the pattern as a literal string
    - Cannot be set to False if pat is a compiled regex or repl is
      a callable.
* **Returns:**
  A copy of the object with all matching occurrences of pat replaced by
  repl.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index) of [object](https://docs.python.org/3/library/functions.html#object)
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – 
  * if regex is False and repl is a callable or pat is a compiled
          regex
        \* if pat is a compiled regex and case or flags is set

### Notes

When pat is a compiled regex, all flags should be included in the
compiled regex. Use of case, flags, or regex=False with a compiled
regex will raise an error.

### Examples

When pat is a string and regex is True, the given pat
is compiled as a regex. When repl is a string, it replaces matching
regex patterns as with `re.sub()`. NaN value(s) in the Series are
left as is:

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> md.Series(['foo', 'fuz', mt.nan]).str.replace('f.', 'ba', regex=True).execute()
0    bao
1    baz
2    NaN
dtype: object
```

When pat is a string and regex is False, every pat is replaced with
repl as with [`str.replace()`](https://docs.python.org/3/library/stdtypes.html#str.replace):

```pycon
>>> md.Series(['f.o', 'fuz', mt.nan]).str.replace('f.', 'ba', regex=False).execute()
0    bao
1    fuz
2    NaN
dtype: object
```

When repl is a callable, it is called on every pat using
[`re.sub()`](https://docs.python.org/3/library/re.html#re.sub). The callable should expect one positional argument
(a regex object) and return a string.

To get the idea:

```pycon
>>> md.Series(['foo', 'fuz', mt.nan]).str.replace('f', repr, regex=True).execute()
0    <re.Match object; span=(0, 1), match='f'>oo
1    <re.Match object; span=(0, 1), match='f'>uz
2                                            NaN
dtype: object
```

Reverse every lowercase alphabetic word:

```pycon
>>> repl = lambda m: m.group(0)[::-1]
>>> ser = md.Series(['foo 123', 'bar baz', mt.nan])
>>> ser.str.replace(r'[a-z]+', repl, regex=True).execute()
0    oof 123
1    rab zab
2        NaN
dtype: object
```

Using regex groups (extract second group and swap case):

```pycon
>>> pat = r"(?P<one>\w+) (?P<two>\w+) (?P<three>\w+)"
>>> repl = lambda m: m.group('two').swapcase()
>>> ser = md.Series(['One Two Three', 'Foo Bar Baz'])
>>> ser.str.replace(pat, repl, regex=True).execute()
0    tWO
1    bAR
dtype: object
```

Using a compiled regex with flags

```pycon
>>> import re
>>> regex_pat = re.compile(r'FUZ', flags=re.IGNORECASE)
>>> md.Series(['foo', 'fuz', mt.nan]).str.replace(regex_pat, 'bar', regex=True).execute()
0    foo
1    bar
2    NaN
dtype: object
```
