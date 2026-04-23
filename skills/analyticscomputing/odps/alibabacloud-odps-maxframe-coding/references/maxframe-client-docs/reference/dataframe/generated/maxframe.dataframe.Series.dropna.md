# maxframe.dataframe.Series.dropna

#### Series.dropna(axis=0, inplace=False, how=None, ignore_index=False)

Return a new Series with missing values removed.

See the [User Guide](https://www.statsmodels.org/devel/missing.html#missing-data) for more on which values are
considered missing, and how to work with missing data.

* **Parameters:**
  * **axis** ( *{0* *or*  *'index'}* *,* *default 0*) – There is only one axis to drop values from.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, do operation inplace and return None.
  * **how** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Not in use. Kept for compatibility.
  * **ignore_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, the resulting axis will be labeled 0, 1, …, n - 1.
* **Returns:**
  Series with NA entries dropped from it.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Series.isna`](maxframe.dataframe.Series.isna.md#maxframe.dataframe.Series.isna)
: Indicate missing values.

[`Series.notna`](maxframe.dataframe.Series.notna.md#maxframe.dataframe.Series.notna)
: Indicate existing (non-missing) values.

[`Series.fillna`](maxframe.dataframe.Series.fillna.md#maxframe.dataframe.Series.fillna)
: Replace missing values.

[`DataFrame.dropna`](maxframe.dataframe.DataFrame.dropna.md#maxframe.dataframe.DataFrame.dropna)
: Drop rows or columns which contain NA values.

[`Index.dropna`](maxframe.dataframe.Index.dropna.md#maxframe.dataframe.Index.dropna)
: Drop missing indices.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> ser = md.Series([1., 2., np.nan])
>>> ser.execute()
0    1.0
1    2.0
2    NaN
dtype: float64
```

Drop NA values from a Series.

```pycon
>>> ser.dropna().execute()
0    1.0
1    2.0
dtype: float64
```

Keep the Series with valid entries in the same variable.

```pycon
>>> ser.dropna(inplace=True)
>>> ser.execute()
0    1.0
1    2.0
dtype: float64
```

Empty strings are not considered NA values. `None` is considered an
NA value.

```pycon
>>> ser = md.Series([np.NaN, '2', md.NaT, '', None, 'I stay'])
>>> ser.execute()
0       NaN
1         2
2       NaT
3
4      None
5    I stay
dtype: object
>>> ser.dropna().execute()
1         2
3
5    I stay
dtype: object
```
