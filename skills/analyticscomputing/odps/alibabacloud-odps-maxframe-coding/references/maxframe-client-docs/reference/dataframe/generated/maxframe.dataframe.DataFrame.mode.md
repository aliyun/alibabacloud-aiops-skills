# maxframe.dataframe.DataFrame.mode

#### DataFrame.mode(axis=0, numeric_only=False, dropna=True, combine_size=None)

Get the mode(s) of each element along the selected axis.

The mode of a set of values is the value that appears most often.
It can be multiple values.

* **Parameters:**
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – 

    The axis to iterate over while searching for the mode:
    * 0 or ‘index’ : get mode of each column
    * 1 or ‘columns’ : get mode of each row.
  * **numeric_only** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, only apply to numeric columns.
  * **dropna** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Don’t consider counts of NaN/NaT.
* **Returns:**
  The modes of each column or row.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`Series.mode`](maxframe.dataframe.Series.mode.md#maxframe.dataframe.Series.mode)
: Return the highest frequency value in a Series.

[`Series.value_counts`](maxframe.dataframe.Series.value_counts.md#maxframe.dataframe.Series.value_counts)
: Return the counts of values in a Series.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([('bird', 2, 2),
...                    ('mammal', 4, mt.nan),
...                    ('arthropod', 8, 0),
...                    ('bird', 2, mt.nan)],
...                   index=('falcon', 'horse', 'spider', 'ostrich'),
...                   columns=('species', 'legs', 'wings'))
>>> df.execute()
           species  legs  wings
falcon        bird     2    2.0
horse       mammal     4    NaN
spider   arthropod     8    0.0
ostrich       bird     2    NaN
```

By default, missing values are not considered, and the mode of wings
are both 0 and 2. Because the resulting DataFrame has two rows,
the second row of `species` and `legs` contains `NaN`.

```pycon
>>> df.mode().execute()
  species  legs  wings
0    bird   2.0    0.0
1     NaN   NaN    2.0
```

Setting `dropna=False` `NaN` values are considered and they can be
the mode (like for wings).

```pycon
>>> df.mode(dropna=False).execute()
  species  legs  wings
0    bird     2    NaN
```

Setting `numeric_only=True`, only the mode of numeric columns is
computed, and columns of other types are ignored.

```pycon
>>> df.mode(numeric_only=True).execute()
   legs  wings
0   2.0    0.0
1   NaN    2.0
```

To compute the mode over columns and not rows, use the axis parameter:

```pycon
>>> df.mode(axis='columns', numeric_only=True).execute()
           0    1
falcon   2.0  NaN
horse    4.0  NaN
spider   0.0  8.0
ostrich  2.0  NaN
```
