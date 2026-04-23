# maxframe.dataframe.DataFrame.notna

#### DataFrame.notna()

Detect existing (non-missing) values.

Return a boolean same-sized object indicating if the values are not NA.
Non-missing values get mapped to True. Characters such as empty
strings `''` or `numpy.inf` are not considered NA values
(unless you set `pandas.options.mode.use_inf_as_na = True`).
NA values, such as None or `numpy.NaN`, get mapped to False
values.

* **Returns:**
  Mask of bool values for each element in DataFrame that
  indicates whether an element is not an NA value.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.notnull`](maxframe.dataframe.DataFrame.notnull.md#maxframe.dataframe.DataFrame.notnull)
: Alias of notna.

[`DataFrame.isna`](maxframe.dataframe.DataFrame.isna.md#maxframe.dataframe.DataFrame.isna)
: Boolean inverse of notna.

[`DataFrame.dropna`](maxframe.dataframe.DataFrame.dropna.md#maxframe.dataframe.DataFrame.dropna)
: Omit axes labels with missing values.

[`notna`](maxframe.dataframe.notna.md#maxframe.dataframe.notna)
: Top-level notna.

### Examples

Show which entries in a DataFrame are not NA.

```pycon
>>> import numpy as np
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'age': [5, 6, np.NaN],
...                    'born': [md.NaT, md.Timestamp('1939-05-27'),
...                             md.Timestamp('1940-04-25')],
...                    'name': ['Alfred', 'Batman', ''],
...                    'toy': [None, 'Batmobile', 'Joker']})
>>> df.execute()
   age       born    name        toy
0  5.0        NaT  Alfred       None
1  6.0 1939-05-27  Batman  Batmobile
2  NaN 1940-04-25              Joker
```

```pycon
>>> df.notna().execute()
     age   born  name    toy
0   True  False  True  False
1   True   True  True   True
2  False   True  True   True
```

Show which entries in a Series are not NA.

```pycon
>>> ser = md.Series([5, 6, np.NaN])
>>> ser.execute()
0    5.0
1    6.0
2    NaN
dtype: float64
```

```pycon
>>> ser.notna().execute()
0     True
1     True
2    False
dtype: bool
```
