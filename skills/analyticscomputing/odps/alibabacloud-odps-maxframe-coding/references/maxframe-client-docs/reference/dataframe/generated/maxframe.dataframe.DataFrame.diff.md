# maxframe.dataframe.DataFrame.diff

#### DataFrame.diff(periods=1, axis=0)

First discrete difference of element.
Calculates the difference of a DataFrame element compared with another
element in the DataFrame (default is the element in the same column
of the previous row).

* **Parameters:**
  * **periods** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 1*) – Periods to shift for calculating difference, accepts negative
    values.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – Take difference over rows (0) or columns (1).
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
`Series.diff`
: First discrete difference for a Series.

[`DataFrame.pct_change`](maxframe.dataframe.DataFrame.pct_change.md#maxframe.dataframe.DataFrame.pct_change)
: Percent change over given number of periods.

[`DataFrame.shift`](maxframe.dataframe.DataFrame.shift.md#maxframe.dataframe.DataFrame.shift)
: Shift index by desired number of periods with an optional time freq.

### Notes

For boolean dtypes, this uses `operator.xor()` rather than
`operator.sub()`.

### Examples

Difference with previous row

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'a': [1, 2, 3, 4, 5, 6],
...                    'b': [1, 1, 2, 3, 5, 8],
...                    'c': [1, 4, 9, 16, 25, 36]})
>>> df.execute()
   a  b   c
0  1  1   1
1  2  1   4
2  3  2   9
3  4  3  16
4  5  5  25
5  6  8  36
```

```pycon
>>> df.diff().execute()
     a    b     c
0  NaN  NaN   NaN
1  1.0  0.0   3.0
2  1.0  1.0   5.0
3  1.0  1.0   7.0
4  1.0  2.0   9.0
5  1.0  3.0  11.0
```

Difference with previous column

```pycon
>>> df.diff(axis=1).execute()
    a    b     c
0 NaN  0.0   0.0
1 NaN -1.0   3.0
2 NaN -1.0   7.0
3 NaN -1.0  13.0
4 NaN  0.0  20.0
5 NaN  2.0  28.0
```

Difference with 3rd previous row

```pycon
>>> df.diff(periods=3).execute()
     a    b     c
0  NaN  NaN   NaN
1  NaN  NaN   NaN
2  NaN  NaN   NaN
3  3.0  2.0  15.0
4  3.0  4.0  21.0
5  3.0  6.0  27.0
```

Difference with following row

```pycon
>>> df.diff(periods=-1).execute()
     a    b     c
0 -1.0  0.0  -3.0
1 -1.0 -1.0  -5.0
2 -1.0 -1.0  -7.0
3 -1.0 -2.0  -9.0
4 -1.0 -3.0 -11.0
5  NaN  NaN   NaN
```
