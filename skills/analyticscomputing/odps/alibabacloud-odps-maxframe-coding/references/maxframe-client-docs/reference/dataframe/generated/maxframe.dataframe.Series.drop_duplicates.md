# maxframe.dataframe.Series.drop_duplicates

#### Series.drop_duplicates(keep='first', inplace=False, ignore_index=False, method='auto', default_index_type=None)

Return Series with duplicate values removed.

* **Parameters:**
  * **keep** ({‘first’, ‘last’, `False`}, default ‘first’) – 

    Method to handle dropping duplicates:
    - ’first’ : Drop duplicates except for the first occurrence.
    - ’last’ : Drop duplicates except for the last occurrence.
    - ’any’ : Drop duplicates except for a random occurrence.
    - `False` : Drop all duplicates.
  * **inplace** (bool, default `False`) – If `True`, performs operation inplace and returns None.
* **Returns:**
  Series with duplicates dropped.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Index.drop_duplicates`](maxframe.dataframe.Index.drop_duplicates.md#maxframe.dataframe.Index.drop_duplicates)
: Equivalent method on Index.

[`DataFrame.drop_duplicates`](maxframe.dataframe.DataFrame.drop_duplicates.md#maxframe.dataframe.DataFrame.drop_duplicates)
: Equivalent method on DataFrame.

`Series.duplicated`
: Related method on Series, indicating duplicate Series values.

### Examples

Generate a Series with duplicated entries.

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(['lame', 'cow', 'lame', 'beetle', 'lame', 'hippo'],
...               name='animal')
>>> s.execute()
0      lame
1       cow
2      lame
3    beetle
4      lame
5     hippo
Name: animal, dtype: object
```

With the ‘keep’ parameter, the selection behaviour of duplicated values
can be changed. The value ‘first’ keeps the first occurrence for each
set of duplicated entries. The default value of keep is ‘first’.
>>> s.drop_duplicates().execute()
0      lame
1       cow
3    beetle
5     hippo
Name: animal, dtype: object
The value ‘last’ for parameter ‘keep’ keeps the last occurrence for
each set of duplicated entries.
>>> s.drop_duplicates(keep=’last’).execute()
1       cow
3    beetle
4      lame
5     hippo
Name: animal, dtype: object

The value `False` for parameter ‘keep’ discards all sets of
duplicated entries. Setting the value of ‘inplace’ to `True` performs
the operation inplace and returns `None`.

```pycon
>>> s.drop_duplicates(keep=False, inplace=True)
>>> s.execute()
1       cow
3    beetle
5     hippo
Name: animal, dtype: object
```
