# maxframe.dataframe.DataFrame.round

#### DataFrame.round(decimals=0, \*args, \*\*kwargs)

Round a DataFrame to a variable number of decimal places.

* **Parameters:**
  * **decimals** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict)) – Number of decimal places to round each column to. If an int is
    given, round each column to the same number of places.
    Otherwise dict and Series round to variable numbers of places.
    Column names should be in the keys if decimals is a
    dict-like. Any columns not included in decimals will be left
    as is. Elements of decimals which are not columns of the
    input will be ignored.
  * **\*args** – Additional keywords have no effect but might be accepted for
    compatibility with numpy.
  * **\*\*kwargs** – Additional keywords have no effect but might be accepted for
    compatibility with numpy.
* **Returns:**
  A DataFrame with the affected columns rounded to the specified
  number of decimal places.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`numpy.around`](https://numpy.org/doc/stable/reference/generated/numpy.around.html#numpy.around)
: Round a numpy array to the given number of decimals.

[`Series.round`](maxframe.dataframe.Series.round.md#maxframe.dataframe.Series.round)
: Round a Series to the given number of decimals.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([(.21, .32), (.01, .67), (.66, .03), (.21, .18)],
...                   columns=['dogs', 'cats'])
>>> df.execute()
    dogs  cats
0  0.21  0.32
1  0.01  0.67
2  0.66  0.03
3  0.21  0.18
```

By providing an integer each column is rounded to the same number
of decimal places

```pycon
>>> df.round(1).execute()
    dogs  cats
0   0.2   0.3
1   0.0   0.7
2   0.7   0.0
3   0.2   0.2
```

With a dict, the number of places for specific columns can be
specified with the column names as key and the number of decimal
places as value

```pycon
>>> df.round({'dogs': 1, 'cats': 0}).execute()
    dogs  cats
0   0.2   0.0
1   0.0   1.0
2   0.7   0.0
3   0.2   0.0
```
