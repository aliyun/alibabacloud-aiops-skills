# maxframe.dataframe.Index.isna

#### Index.isna()

Detect missing values.

Return a boolean same-sized object indicating if the values are NA.
NA values, such as None or `numpy.NaN`, gets mapped to True
values.

Everything else gets mapped to False values. Characters such as empty
strings `''` or `numpy.inf` are not considered NA values
(unless you set `pandas.options.mode.use_inf_as_na = True`).

* **Returns:**
  Mask of bool values for each element in DataFrame that
  indicates whether an element is not an NA value.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.isnull`](maxframe.dataframe.DataFrame.isnull.md#maxframe.dataframe.DataFrame.isnull)
: Alias of isna.

[`DataFrame.notna`](maxframe.dataframe.DataFrame.notna.md#maxframe.dataframe.DataFrame.notna)
: Boolean inverse of isna.

[`DataFrame.dropna`](maxframe.dataframe.DataFrame.dropna.md#maxframe.dataframe.DataFrame.dropna)
: Omit axes labels with missing values.

[`isna`](maxframe.dataframe.isna.md#maxframe.dataframe.isna)
: Top-level isna.

### Examples

Show which entries in a DataFrame are NA.

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
>>> df.isna().execute()
     age   born   name    toy
0  False   True  False   True
1  False  False  False  False
2   True  False  False  False
```

Show which entries in a Series are NA.

```pycon
>>> ser = md.Series([5, 6, np.NaN])
>>> ser.execute()
0    5.0
1    6.0
2    NaN
dtype: float64
```

```pycon
>>> ser.isna().execute()
0    False
1    False
2     True
dtype: bool
```
