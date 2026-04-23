# maxframe.dataframe.DataFrame.dropna

#### DataFrame.dropna(axis=0, how=<no_default>, thresh=<no_default>, subset=None, inplace=False, ignore_index=False)

Remove missing values.

See the [User Guide](https://www.statsmodels.org/devel/missing.html#missing-data) for more on which values are
considered missing, and how to work with missing data.

* **Parameters:**
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – 

    Determine if rows or columns which contain missing values are
    removed.
    * 0, or ‘index’ : Drop rows which contain missing values.
    * 1, or ‘columns’ : Drop columns which contain missing value.
  * **how** ( *{'any'* *,*  *'all'}* *,* *default 'any'*) – 

    Determine if row or column is removed from DataFrame, when we have
    at least one NA or all NA.
    * ’any’ : If any NA values are present, drop that row or column.
    * ’all’ : If all values are NA, drop that row or column.
  * **thresh** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Require that many non-NA values.
  * **subset** (*array-like* *,* *optional*) – Labels along other axis to consider, e.g. if you are dropping rows
    these would be a list of columns to include.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, do operation inplace and return None.
  * **ignore_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, the resulting axis will be labeled 0, 1, …, n - 1.
* **Returns:**
  DataFrame with NA entries dropped from it.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.isna`](maxframe.dataframe.DataFrame.isna.md#maxframe.dataframe.DataFrame.isna)
: Indicate missing values.

[`DataFrame.notna`](maxframe.dataframe.DataFrame.notna.md#maxframe.dataframe.DataFrame.notna)
: Indicate existing (non-missing) values.

[`DataFrame.fillna`](maxframe.dataframe.DataFrame.fillna.md#maxframe.dataframe.DataFrame.fillna)
: Replace missing values.

[`Series.dropna`](maxframe.dataframe.Series.dropna.md#maxframe.dataframe.Series.dropna)
: Drop missing values.

[`Index.dropna`](maxframe.dataframe.Index.dropna.md#maxframe.dataframe.Index.dropna)
: Drop missing indices.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({"name": ['Alfred', 'Batman', 'Catwoman'],
...                    "toy": [np.nan, 'Batmobile', 'Bullwhip'],
...                    "born": [md.NaT, md.Timestamp("1940-04-25"),
...                             md.NaT]})
>>> df.execute()
       name        toy       born
0    Alfred        NaN        NaT
1    Batman  Batmobile 1940-04-25
2  Catwoman   Bullwhip        NaT
```

Drop the rows where at least one element is missing.

```pycon
>>> df.dropna().execute()
     name        toy       born
1  Batman  Batmobile 1940-04-25
```

Drop the rows where all elements are missing.

```pycon
>>> df.dropna(how='all').execute()
       name        toy       born
0    Alfred        NaN        NaT
1    Batman  Batmobile 1940-04-25
2  Catwoman   Bullwhip        NaT
```

Keep only the rows with at least 2 non-NA values.

```pycon
>>> df.dropna(thresh=2).execute()
       name        toy       born
1    Batman  Batmobile 1940-04-25
2  Catwoman   Bullwhip        NaT
```

Define in which columns to look for missing values.

```pycon
>>> df.dropna(subset=['name', 'born']).execute()
       name        toy       born
1    Batman  Batmobile 1940-04-25
```

Keep the DataFrame with valid entries in the same variable.

```pycon
>>> df.dropna(inplace=True)
>>> df.execute()
     name        toy       born
1  Batman  Batmobile 1940-04-25
```
