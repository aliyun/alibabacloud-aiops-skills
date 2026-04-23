# maxframe.dataframe.DataFrame.ne

#### DataFrame.ne(other, axis='columns', level=None, fill_value=None)

Get Not equal to of dataframe and other, element-wise (binary operator ne).
Among flexible wrappers (eq, ne, le, lt, ge, gt) to comparison
operators.

Equivalent to dataframe != other with support to choose axis (rows or columns)
and level for comparison.

* **Parameters:**
  * **other** (*scalar* *,* *sequence* *,* [*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *, or* [*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)) – Any single or multiple element data structure, or list-like object.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 'columns'*) – Whether to compare by the index (0 or ‘index’) or columns
    (1 or ‘columns’).
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *label*) – Broadcast across a level, matching Index values on the passed
    MultiIndex level.
* **Returns:**
  Result of the comparison.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) of [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`DataFrame.eq`](maxframe.dataframe.DataFrame.eq.md#maxframe.dataframe.DataFrame.eq)
: Compare DataFrames for equality elementwise.

[`DataFrame.ne`](#maxframe.dataframe.DataFrame.ne)
: Compare DataFrames for inequality elementwise.

[`DataFrame.le`](maxframe.dataframe.DataFrame.le.md#maxframe.dataframe.DataFrame.le)
: Compare DataFrames for less than inequality or equality elementwise.

[`DataFrame.lt`](maxframe.dataframe.DataFrame.lt.md#maxframe.dataframe.DataFrame.lt)
: Compare DataFrames for strictly less than inequality elementwise.

[`DataFrame.ge`](maxframe.dataframe.DataFrame.ge.md#maxframe.dataframe.DataFrame.ge)
: Compare DataFrames for greater than inequality or equality elementwise.

[`DataFrame.gt`](maxframe.dataframe.DataFrame.gt.md#maxframe.dataframe.DataFrame.gt)
: Compare DataFrames for strictly greater than inequality elementwise.

### Notes

Mismatched indices will be unioned together.
NaN values are considered different (i.e. NaN != NaN).

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'cost': [250, 150, 100],
...                    'revenue': [100, 250, 300]},
...                   index=['A', 'B', 'C'])
>>> df.execute()
   cost  revenue
A   250      100
B   150      250
C   100      300
```

Comparison with a scalar, using either the operator or method:

```pycon
>>> (df == 100).execute()
    cost  revenue
A  False     True
B  False    False
C   True    False
```

```pycon
>>> df.eq(100).execute()
    cost  revenue
A  False     True
B  False    False
C   True    False
```

When other is a [`Series`](maxframe.dataframe.Series.md#maxframe.dataframe.Series), the columns of a DataFrame are aligned
with the index of other and broadcast:

```pycon
>>> (df != pd.Series([100, 250], index=["cost", "revenue"])).execute()
    cost  revenue
A   True     True
B   True    False
C  False     True
```

Use the method to control the broadcast axis:

```pycon
>>> df.ne(pd.Series([100, 300], index=["A", "D"]), axis='index').execute()
   cost  revenue
A  True    False
B  True     True
C  True     True
D  True     True
```

When comparing to an arbitrary sequence, the number of columns must
match the number elements in other:

```pycon
>>> (df == [250, 100]).execute()
    cost  revenue
A   True     True
B  False    False
C  False    False
```

Use the method to control the axis:

```pycon
>>> df.eq([250, 250, 100], axis='index').execute()
    cost  revenue
A   True    False
B  False     True
C   True    False
```

Compare to a DataFrame of different shape.

```pycon
>>> other = md.DataFrame({'revenue': [300, 250, 100, 150]},
...                      index=['A', 'B', 'C', 'D'])
>>> other.execute()
   revenue
A      300
B      250
C      100
D      150
```

```pycon
>>> df.gt(other).execute()
    cost  revenue
A  False    False
B  False    False
C  False     True
D  False    False
```

Compare to a MultiIndex by level.

```pycon
>>> df_multindex = md.DataFrame({'cost': [250, 150, 100, 150, 300, 220],
...                              'revenue': [100, 250, 300, 200, 175, 225]},
...                             index=[['Q1', 'Q1', 'Q1', 'Q2', 'Q2', 'Q2'],
...                                    ['A', 'B', 'C', 'A', 'B', 'C']])
>>> df_multindex.execute()
      cost  revenue
Q1 A   250      100
   B   150      250
   C   100      300
Q2 A   150      200
   B   300      175
   C   220      225
```

```pycon
>>> df.le(df_multindex, level=1).execute()
       cost  revenue
Q1 A   True     True
   B   True     True
   C   True     True
Q2 A  False     True
   B   True    False
   C   True    False
```
