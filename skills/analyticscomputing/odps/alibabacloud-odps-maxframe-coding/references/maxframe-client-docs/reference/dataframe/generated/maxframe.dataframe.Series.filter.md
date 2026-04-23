# maxframe.dataframe.Series.filter

#### Series.filter(items=None, like=None, regex=None, axis=None)

Subset the dataframe rows or columns according to the specified index labels.

Note that this routine does not filter a dataframe on its
contents. The filter is applied to the labels of the index.

* **Parameters:**
  * **items** (*list-like*) – Keep labels from axis which are in items.
  * **like** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Keep labels from axis for which “like in label == True”.
  * **regex** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *(**regular expression* *)*) – Keep labels from axis for which re.search(regex, label) == True.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'* *,* *None}* *,* *default None*) – The axis to filter on, expressed either as an index (int)
    or axis name (str). By default this is the info axis, ‘columns’ for
    DataFrame. For Series this parameter is unused and defaults to None.
* **Return type:**
  same type as input object

#### SEE ALSO
[`DataFrame.loc`](maxframe.dataframe.DataFrame.loc.md#maxframe.dataframe.DataFrame.loc)
: Access a group of rows and columns by label(s) or a boolean array.

### Notes

The `items`, `like`, and `regex` parameters are
enforced to be mutually exclusive.

`axis` defaults to the info axis that is used when indexing
with `[]`.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame(mt.array(([1, 2, 3], [4, 5, 6])),
...                   index=['mouse', 'rabbit'],
...                   columns=['one', 'two', 'three'])
>>> df.execute()
        one  two  three
mouse     1    2      3
rabbit    4    5      6
```

```pycon
>>> # select columns by name
>>> df.filter(items=['one', 'three']).execute()
         one  three
mouse     1      3
rabbit    4      6
```

```pycon
>>> # select columns by regular expression
>>> df.filter(regex='e$', axis=1).execute()
         one  three
mouse     1      3
rabbit    4      6
```

```pycon
>>> # select rows containing 'bbi'
>>> df.filter(like='bbi', axis=0).execute()
         one  two  three
rabbit    4    5      6
```
