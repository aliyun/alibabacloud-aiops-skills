# maxframe.dataframe.DataFrame.melt

#### DataFrame.melt(id_vars=None, value_vars=None, var_name=None, value_name='value', col_level=None, ignore_index=False, default_index_type=None)

Unpivot a DataFrame from wide to long format, optionally leaving identifiers set.

This function is useful to massage a DataFrame into a format where one
or more columns are identifier variables (id_vars), while all other
columns, considered measured variables (value_vars), are “unpivoted” to
the row axis, leaving just two non-identifier columns, ‘variable’ and
‘value’.

* **Parameters:**
  * **id_vars** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *,* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *, or* *ndarray* *,* *optional*) – Column(s) to use as identifier variables.
  * **value_vars** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *,* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *, or* *ndarray* *,* *optional*) – Column(s) to unpivot. If not specified, uses all columns that
    are not set as id_vars.
  * **var_name** (*scalar*) – Name to use for the ‘variable’ column. If None it uses
    `frame.columns.name` or ‘variable’.
  * **value_name** (*scalar* *,* *default 'value'*) – Name to use for the ‘value’ column.
  * **col_level** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – If columns are a MultiIndex then use this level to melt.
  * **ignore_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If True, original index is ignored. If False, the original index
    is retained. Index labels will be repeated as necessary.
* **Returns:**
  Unpivoted DataFrame.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`melt`](#maxframe.dataframe.DataFrame.melt), [`pivot_table`](maxframe.dataframe.DataFrame.pivot_table.md#maxframe.dataframe.DataFrame.pivot_table), [`DataFrame.pivot`](maxframe.dataframe.DataFrame.pivot.md#maxframe.dataframe.DataFrame.pivot), [`Series.explode`](maxframe.dataframe.Series.explode.md#maxframe.dataframe.Series.explode)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'A': {0: 'a', 1: 'b', 2: 'c'},
...                    'B': {0: 1, 1: 3, 2: 5},
...                    'C': {0: 2, 1: 4, 2: 6}})
>>> df.execute()
   A  B  C
0  a  1  2
1  b  3  4
2  c  5  6
```

```pycon
>>> df.melt(id_vars=['A'], value_vars=['B']).execute()
   A variable  value
0  a        B      1
1  b        B      3
2  c        B      5
```

```pycon
>>> df.melt(id_vars=['A'], value_vars=['B', 'C']).execute()
   A variable  value
0  a        B      1
1  b        B      3
2  c        B      5
3  a        C      2
4  b        C      4
5  c        C      6
```

The names of ‘variable’ and ‘value’ columns can be customized:

```pycon
>>> df.melt(id_vars=['A'], value_vars=['B'],
...         var_name='myVarname', value_name='myValname').execute()
   A myVarname  myValname
0  a         B          1
1  b         B          3
2  c         B          5
```

If you have multi-index columns:

```pycon
>>> df = md.DataFrame({('A', 'D'): {0: 'a', 1: 'b', 2: 'c'},
...                    ('B', 'E'): {0: 1, 1: 3, 2: 5},
...                    ('C', 'F'): {0: 2, 1: 4, 2: 6}})
>>> df.execute()
   A  B  C
   D  E  F
0  a  1  2
1  b  3  4
2  c  5  6
```

```pycon
>>> df.melt(col_level=0, id_vars=['A'], value_vars=['B']).execute()
   A variable  value
0  a        B      1
1  b        B      3
2  c        B      5
```

```pycon
>>> df.melt(id_vars=[('A', 'D')], value_vars=[('B', 'E')]).execute()
  (A, D) variable_0 variable_1  value
0      a          B          E      1
1      b          B          E      3
2      c          B          E      5
```
