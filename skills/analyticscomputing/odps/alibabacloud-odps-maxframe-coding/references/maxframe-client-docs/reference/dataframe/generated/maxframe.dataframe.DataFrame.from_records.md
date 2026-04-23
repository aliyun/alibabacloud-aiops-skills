# maxframe.dataframe.DataFrame.from_records

#### *static* DataFrame.from_records(data, index=None, exclude=None, columns=None, coerce_float=False, nrows=None, gpu=None, sparse=False, \*\*kw)

Convert structured or record ndarray to DataFrame.

Creates a DataFrame object from a structured ndarray, sequence of
tuples or dicts, or DataFrame.

* **Parameters:**
  * **data** (*structured ndarray* *,* *sequence* *of* *tuples* *or* *dicts* *, or* [*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)) – 

    Structured input data.

    #### Deprecated
    Deprecated since version 2.1.0: Passing a DataFrame is deprecated.
  * **index** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *fields* *,* *array-like*) – Field of array to use as the index, alternately a specific set of
    input labels to use.
  * **exclude** (*sequence* *,* *default None*) – Columns or fields to exclude.
  * **columns** (*sequence* *,* *default None*) – Column names to use. If the passed data do not have names
    associated with them, this argument provides names for the
    columns. Otherwise this argument indicates the order of the columns
    in the result (any names not found in the data will become all-NA
    columns).
  * **coerce_float** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Attempt to convert values of non-string, non-numeric objects (like
    decimal.Decimal) to floating point, useful for SQL result sets.
  * **nrows** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default None*) – Number of rows to read if data is an iterator.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.from_dict`](maxframe.dataframe.DataFrame.from_dict.md#maxframe.dataframe.DataFrame.from_dict)
: DataFrame from dict of array-like or dicts.

[`DataFrame`](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
: DataFrame object creation using constructor.

### Examples

Data can be provided as a structured ndarray:

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> data = mt.array([(3, 'a'), (2, 'b'), (1, 'c'), (0, 'd')],
...                 dtype=[('col_1', 'i4'), ('col_2', 'U1')])
>>> md.DataFrame.from_records(data).execute()
   col_1 col_2
0      3     a
1      2     b
2      1     c
3      0     d
```

Data can be provided as a list of dicts:

```pycon
>>> data = [{'col_1': 3, 'col_2': 'a'},
...         {'col_1': 2, 'col_2': 'b'},
...         {'col_1': 1, 'col_2': 'c'},
...         {'col_1': 0, 'col_2': 'd'}]
>>> md.DataFrame.from_records(data).execute()
   col_1 col_2
0      3     a
1      2     b
2      1     c
3      0     d
```

Data can be provided as a list of tuples with corresponding columns:

```pycon
>>> data = [(3, 'a'), (2, 'b'), (1, 'c'), (0, 'd')]
>>> md.DataFrame.from_records(data, columns=['col_1', 'col_2']).execute()
   col_1 col_2
0      3     a
1      2     b
2      1     c
3      0     d
```
