# maxframe.dataframe.DataFrame.set_index

#### DataFrame.set_index(keys, drop=True, append=False, inplace=False, verify_integrity=False)

Set the DataFrame index using existing columns.

Set the DataFrame index (row labels) using one or more existing
columns. The index can replace the existing index or expand on it.

* **Parameters:**
  * **keys** (*label* *or* *array-like* *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *labels*) – This parameter can be either a single column key, or a list containing column keys.
  * **drop** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Delete columns to be used as the new index.
  * **append** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether to append columns to existing index.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, modifies the DataFrame in place (do not create a new object).
  * **verify_integrity** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Check the new index for duplicates. Otherwise defer the check until
    necessary. Setting to False will improve the performance of this
    method.
* **Returns:**
  Changed row labels or None if `inplace=True`.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) or None

#### SEE ALSO
[`DataFrame.reset_index`](maxframe.dataframe.DataFrame.reset_index.md#maxframe.dataframe.DataFrame.reset_index)
: Opposite of set_index.

[`DataFrame.reindex`](maxframe.dataframe.DataFrame.reindex.md#maxframe.dataframe.DataFrame.reindex)
: Change to new indices or expand indices.

[`DataFrame.reindex_like`](maxframe.dataframe.DataFrame.reindex_like.md#maxframe.dataframe.DataFrame.reindex_like)
: Change to same indices as other DataFrame.

### Examples

```pycon
>>> import maxframe.dataframe as md
```

```pycon
>>> df = md.DataFrame({'month': [1, 4, 7, 10],
...                    'year': [2012, 2014, 2013, 2014],
...                    'sale': [55, 40, 84, 31]})
>>> df
   month  year  sale
0      1  2012    55
1      4  2014    40
2      7  2013    84
3     10  2014    31
```

Set the index to become the ‘month’ column:

```pycon
>>> df.set_index('month')
       year  sale
month
1      2012    55
4      2014    40
7      2013    84
10     2014    31
```

Create a MultiIndex using columns ‘year’ and ‘month’:

```pycon
>>> df.set_index(['year', 'month'])
            sale
year  month
2012  1     55
2014  4     40
2013  7     84
2014  10    31
```
