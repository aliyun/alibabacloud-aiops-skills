# maxframe.dataframe.DataFrame.from_dict

#### *static* DataFrame.from_dict(data, orient='columns', dtype=None, columns=None)

Construct DataFrame from dict of array-like or dicts.

Creates DataFrame object from dictionary by columns or by index
allowing dtype specification.

* **Parameters:**
  * **data** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict)) – Of the form {field : array-like} or {field : dict}.
  * **orient** ( *{'columns'* *,*  *'index'* *,*  *'tight'}* *,* *default 'columns'*) – The “orientation” of the data. If the keys of the passed dict
    should be the columns of the resulting DataFrame, pass ‘columns’
    (default). Otherwise if the keys should be rows, pass ‘index’.
    If ‘tight’, assume a dict with keys [‘index’, ‘columns’, ‘data’,
    ‘index_names’, ‘column_names’].
  * **dtype** (*dtype* *,* *default None*) – Data type to force after DataFrame construction, otherwise infer.
  * **columns** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* *default None*) – Column labels to use when `orient='index'`. Raises a ValueError
    if used with `orient='columns'` or `orient='tight'`.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.from_records`](maxframe.dataframe.DataFrame.from_records.md#maxframe.dataframe.DataFrame.from_records)
: DataFrame from structured ndarray, sequence of tuples or dicts, or DataFrame.

[`DataFrame`](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
: DataFrame object creation using constructor.

[`DataFrame.to_dict`](maxframe.dataframe.DataFrame.to_dict.md#maxframe.dataframe.DataFrame.to_dict)
: Convert the DataFrame to a dictionary.

### Examples

By default the keys of the dict become the DataFrame columns:

```pycon
>>> import maxframe.dataframe as md
>>> data = {'col_1': [3, 2, 1, 0], 'col_2': ['a', 'b', 'c', 'd']}
>>> md.DataFrame.from_dict(data).execute()
   col_1 col_2
0      3     a
1      2     b
2      1     c
3      0     d
```

Specify `orient='index'` to create the DataFrame using dictionary
keys as rows:

```pycon
>>> data = {'row_1': [3, 2, 1, 0], 'row_2': ['a', 'b', 'c', 'd']}
>>> md.DataFrame.from_dict(data, orient='index').execute()
       0  1  2  3
row_1  3  2  1  0
row_2  a  b  c  d
```

When using the ‘index’ orientation, the column names can be
specified manually:

```pycon
>>> md.DataFrame.from_dict(data, orient='index',
...                        columns=['A', 'B', 'C', 'D']).execute()
       A  B  C  D
row_1  3  2  1  0
row_2  a  b  c  d
```

Specify `orient='tight'` to create the DataFrame using a ‘tight’
format:

```pycon
>>> data = {'index': [('a', 'b'), ('a', 'c')],
...         'columns': [('x', 1), ('y', 2)],
...         'data': [[1, 3], [2, 4]],
...         'index_names': ['n1', 'n2'],
...         'column_names': ['z1', 'z2']}
>>> md.DataFrame.from_dict(data, orient='tight').execute()
z1     x  y
z2     1  2
n1 n2
a  b   1  3
   c   2  4
```
