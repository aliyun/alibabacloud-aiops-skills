# maxframe.dataframe.DataFrame.duplicated

#### DataFrame.duplicated(subset=None, keep='first', method='auto')

Return boolean Series denoting duplicate rows.

Considering certain columns is optional.

* **Parameters:**
  * **subset** (*column label* *or* *sequence* *of* *labels* *,* *optional*) – Only consider certain columns for identifying duplicates, by
    default use all of the columns.
  * **keep** ( *{'first'* *,*  *'last'* *,* *False}* *,* *default 'first'*) – 

    Determines which duplicates (if any) to mark.
    - `first` : Mark duplicates as `True` except for the first occurrence.
    - `last` : Mark duplicates as `True` except for the last occurrence.
    - False : Mark all duplicates as `True`.
* **Returns:**
  Boolean series for each duplicated rows.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
`Index.duplicated`
: Equivalent method on index.

`Series.duplicated`
: Equivalent method on Series.

[`Series.drop_duplicates`](maxframe.dataframe.Series.drop_duplicates.md#maxframe.dataframe.Series.drop_duplicates)
: Remove duplicate values from Series.

[`DataFrame.drop_duplicates`](maxframe.dataframe.DataFrame.drop_duplicates.md#maxframe.dataframe.DataFrame.drop_duplicates)
: Remove duplicate values from DataFrame.

### Examples

Consider dataset containing ramen rating.

```pycon
>>> import maxframe.dataframe as md
```

```pycon
>>> df = md.DataFrame({
...     'brand': ['Yum Yum', 'Yum Yum', 'Indomie', 'Indomie', 'Indomie'],
...     'style': ['cup', 'cup', 'cup', 'pack', 'pack'],
...     'rating': [4, 4, 3.5, 15, 5]
... })
>>> df.execute()
    brand style  rating
0  Yum Yum   cup     4.0
1  Yum Yum   cup     4.0
2  Indomie   cup     3.5
3  Indomie  pack    15.0
4  Indomie  pack     5.0
```

By default, for each set of duplicated values, the first occurrence
is set on False and all others on True.

```pycon
>>> df.duplicated().execute()
0    False
1     True
2    False
3    False
4    False
dtype: bool
```

By using ‘last’, the last occurrence of each set of duplicated values
is set on False and all others on True.

```pycon
>>> df.duplicated(keep='last').execute()
0     True
1    False
2    False
3    False
4    False
dtype: bool
```

By setting `keep` on False, all duplicates are True.

```pycon
>>> df.duplicated(keep=False).execute()
0     True
1     True
2    False
3    False
4    False
dtype: bool
```

To find duplicates on specific column(s), use `subset`.

```pycon
>>> df.duplicated(subset=['brand']).execute()
0    False
1     True
2    False
3     True
4     True
dtype: bool
```
