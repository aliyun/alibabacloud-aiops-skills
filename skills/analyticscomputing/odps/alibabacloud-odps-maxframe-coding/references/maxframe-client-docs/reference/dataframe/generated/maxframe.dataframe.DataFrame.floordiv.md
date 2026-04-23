# maxframe.dataframe.DataFrame.floordiv

#### DataFrame.floordiv(other, axis='columns', level=None, fill_value=None)

Get Integer division of dataframe and other, element-wise (binary operator floordiv).
Equivalent to `//`, but with support to substitute a fill_value
for missing data in one of the inputs. With reverse version, rfloordiv.
Among flexible wrappers (add, sub, mul, div, mod, pow) to
arithmetic operators: +, -, \*, /, //, %, \*\*.

* **Parameters:**
  * **other** (*scalar* *,* *sequence* *,* [*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *, or* [*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)) – Any single or multiple element data structure, or list-like object.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}*) – Whether to compare by the index (0 or ‘index’) or columns
    (1 or ‘columns’). For Series input, axis to match Series index on.
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *label*) – Broadcast across a level, matching Index values on the
    passed MultiIndex level.
  * **fill_value** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *None* *,* *default None*) – Fill existing missing (NaN) values, and any new element needed for
    successful DataFrame alignment, with this value before computation.
    If data in both corresponding DataFrame locations is missing
    the result will be missing.
* **Returns:**
  Result of the arithmetic operation.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.add`](maxframe.dataframe.DataFrame.add.md#maxframe.dataframe.DataFrame.add)
: Add DataFrames.

[`DataFrame.sub`](maxframe.dataframe.DataFrame.sub.md#maxframe.dataframe.DataFrame.sub)
: Subtract DataFrames.

[`DataFrame.mul`](maxframe.dataframe.DataFrame.mul.md#maxframe.dataframe.DataFrame.mul)
: Multiply DataFrames.

[`DataFrame.div`](maxframe.dataframe.DataFrame.div.md#maxframe.dataframe.DataFrame.div)
: Divide DataFrames (float division).

[`DataFrame.truediv`](maxframe.dataframe.DataFrame.truediv.md#maxframe.dataframe.DataFrame.truediv)
: Divide DataFrames (float division).

[`DataFrame.floordiv`](#maxframe.dataframe.DataFrame.floordiv)
: Divide DataFrames (integer division).

[`DataFrame.mod`](maxframe.dataframe.DataFrame.mod.md#maxframe.dataframe.DataFrame.mod)
: Calculate modulo (remainder after division).

[`DataFrame.pow`](maxframe.dataframe.DataFrame.pow.md#maxframe.dataframe.DataFrame.pow)
: Calculate exponential power.

### Notes

Mismatched indices will be unioned together.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'angles': [0, 3, 4],
...                    'degrees': [360, 180, 360]},
...                   index=['circle', 'triangle', 'rectangle'])
>>> df.execute()
           angles  degrees
circle          0      360
triangle        3      180
rectangle       4      360
```

Add a scalar with operator version which return the same
results.

```pycon
>>> (df + 1).execute()
           angles  degrees
circle          1      361
triangle        4      181
rectangle       5      361
```

```pycon
>>> df.add(1).execute()
           angles  degrees
circle          1      361
triangle        4      181
rectangle       5      361
```

Divide by constant with reverse version.

```pycon
>>> df.div(10).execute()
           angles  degrees
circle        0.0     36.0
triangle      0.3     18.0
rectangle     0.4     36.0
```

```pycon
>>> df.rdiv(10).execute()
             angles   degrees
circle          inf  0.027778
triangle   3.333333  0.055556
rectangle  2.500000  0.027778
```

Subtract a list and Series by axis with operator version.

```pycon
>>> (df - [1, 2]).execute()
           angles  degrees
circle         -1      358
triangle        2      178
rectangle       3      358
```

```pycon
>>> df.sub([1, 2], axis='columns').execute()
           angles  degrees
circle         -1      358
triangle        2      178
rectangle       3      358
```

```pycon
>>> df.sub(md.Series([1, 1, 1], index=['circle', 'triangle', 'rectangle']),
...        axis='index').execute()
           angles  degrees
circle         -1      359
triangle        2      179
rectangle       3      359
```

Multiply a DataFrame of different shape with operator version.

```pycon
>>> other = md.DataFrame({'angles': [0, 3, 4]},
...                      index=['circle', 'triangle', 'rectangle'])
>>> other.execute()
           angles
circle          0
triangle        3
rectangle       4
```

```pycon
>>> df.mul(other, fill_value=0).execute()
           angles  degrees
circle          0      0.0
triangle        9      0.0
rectangle      16      0.0
```
