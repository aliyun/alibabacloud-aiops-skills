# maxframe.dataframe.Index.drop_duplicates

#### Index.drop_duplicates(keep='first', method='auto')

Return Index with duplicate values removed.

* **Parameters:**
  **keep** ({‘first’, ‘last’, `False`}, default ‘first’) – 
  - ‘first’ : Drop duplicates except for the first occurrence.
  - ’last’ : Drop duplicates except for the last occurrence.
  - ’any’ : Drop duplicates except for a random occurrence.
  - `False` : Drop all duplicates.
* **Returns:**
  **deduplicated**
* **Return type:**
  [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

#### SEE ALSO
[`Series.drop_duplicates`](maxframe.dataframe.Series.drop_duplicates.md#maxframe.dataframe.Series.drop_duplicates)
: Equivalent method on Series.

[`DataFrame.drop_duplicates`](maxframe.dataframe.DataFrame.drop_duplicates.md#maxframe.dataframe.DataFrame.drop_duplicates)
: Equivalent method on DataFrame.

`Index.duplicated`
: Related method on Index, indicating duplicate Index values.

### Examples

Generate a pandas.Index with duplicate values.

```pycon
>>> import maxframe.dataframe as md
```

```pycon
>>> idx = md.Index(['lame', 'cow', 'lame', 'beetle', 'lame', 'hippo'])
```

The keep parameter controls  which duplicate values are removed.
The value ‘first’ keeps the first occurrence for each
set of duplicated entries. The default value of keep is ‘first’.

```pycon
>>> idx.drop_duplicates(keep='first').execute()
Index(['lame', 'cow', 'beetle', 'hippo'], dtype='object')
```

The value ‘last’ keeps the last occurrence for each set of duplicated
entries.

```pycon
>>> idx.drop_duplicates(keep='last').execute()
Index(['cow', 'beetle', 'lame', 'hippo'], dtype='object')
```

The value `False` discards all sets of duplicated entries.

```pycon
>>> idx.drop_duplicates(keep=False).execute()
Index(['cow', 'beetle', 'hippo'], dtype='object')
```
