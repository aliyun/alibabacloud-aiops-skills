# maxframe.dataframe.DataFrame.update

#### DataFrame.update(other, join='left', overwrite=True, filter_func=None, errors='ignore')

Modify in place using non-NA values from another DataFrame.

Aligns on indices. There is no return value.

* **Parameters:**
  * **other** ([*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) *, or* *object coercible into a DataFrame*) – Should have at least one matching index/column label
    with the original DataFrame. If a Series is passed,
    its name attribute must be set, and that will be
    used as the column name to align with the original DataFrame.
  * **join** ( *{'left'}* *,* *default 'left'*) – Only left join is implemented, keeping the index and columns of the
    original object.
  * **overwrite** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – 

    How to handle non-NA values for overlapping keys:
    * True: overwrite original DataFrame’s values
      with values from other.
    * False: only update values that are NA in
      the original DataFrame.
  * **filter_func** (*callable* *(**1d-array* *)*  *-> bool 1d-array* *,* *optional*) – Can choose to replace values other than NA. Return True for values
    that should be updated.
  * **errors** ( *{'raise'* *,*  *'ignore'}* *,* *default 'ignore'*) – If ‘raise’, will raise a ValueError if the DataFrame and other
    both contain non-NA data in the same place.
* **Returns:**
  This method directly changes calling object.
* **Return type:**
  None
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – 
    * When errors=’raise’ and there’s overlapping non-NA data.
          \* When errors is not either ‘ignore’ or ‘raise’
  * [**NotImplementedError**](https://docs.python.org/3/library/exceptions.html#NotImplementedError) – 
    * If join != ‘left’

#### SEE ALSO
[`dict.update`](https://docs.python.org/3/library/stdtypes.html#dict.update)
: Similar method for dictionaries.

[`DataFrame.merge`](maxframe.dataframe.DataFrame.merge.md#maxframe.dataframe.DataFrame.merge)
: For column(s)-on-column(s) operations.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'A': [1, 2, 3],
...                    'B': [400, 500, 600]})
>>> new_df = md.DataFrame({'B': [4, 5, 6],
...                        'C': [7, 8, 9]})
>>> df.update(new_df)
>>> df.execute()
   A  B
0  1  4
1  2  5
2  3  6
```

The DataFrame’s length does not increase as a result of the update,
only values at matching index/column labels are updated.

```pycon
>>> df = md.DataFrame({'A': ['a', 'b', 'c'],
...                    'B': ['x', 'y', 'z']})
>>> new_df = md.DataFrame({'B': ['d', 'e', 'f', 'g', 'h', 'i']})
>>> df.update(new_df)
>>> df.execute()
   A  B
0  a  d
1  b  e
2  c  f
```

```pycon
>>> df = md.DataFrame({'A': ['a', 'b', 'c'],
...                    'B': ['x', 'y', 'z']})
>>> new_df = md.DataFrame({'B': ['d', 'f']}, index=[0, 2])
>>> df.update(new_df)
>>> df.execute()
   A  B
0  a  d
1  b  y
2  c  f
```

For Series, its name attribute must be set.

```pycon
>>> df = md.DataFrame({'A': ['a', 'b', 'c'],
...                    'B': ['x', 'y', 'z']})
>>> new_column = md.Series(['d', 'e', 'f'], name='B')
>>> df.update(new_column)
>>> df.execute()
   A  B
0  a  d
1  b  e
2  c  f
```

If other contains NaNs the corresponding values are not updated
in the original dataframe.

```pycon
>>> df = md.DataFrame({'A': [1, 2, 3],
...                    'B': [400., 500., 600.]})
>>> new_df = md.DataFrame({'B': [4, mt.nan, 6]})
>>> df.update(new_df)
>>> df.execute()
   A      B
0  1    4.0
1  2  500.0
2  3    6.0
```
