# maxframe.dataframe.DataFrame.pivot_table

#### DataFrame.pivot_table(values=None, index=None, columns=None, aggfunc='mean', fill_value=None, margins=False, dropna=True, margins_name='All', sort=True)

Create a spreadsheet-style pivot table as a DataFrame.

The levels in the pivot table will be stored in MultiIndex objects
(hierarchical indexes) on the index and columns of the result DataFrame.

* **Parameters:**
  * **values** (*column to aggregate* *,* *optional*)
  * **index** (*column* *,* *Grouper* *,* *array* *, or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *the previous*) – If an array is passed, it must be the same length as the data. The
    list can contain any of the other types (except list).
    Keys to group by on the pivot table index.  If an array is passed,
    it is being used as the same manner as column values.
  * **columns** (*column* *,* *Grouper* *,* *array* *, or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *the previous*) – If an array is passed, it must be the same length as the data. The
    list can contain any of the other types (except list).
    Keys to group by on the pivot table column.  If an array is passed,
    it is being used as the same manner as column values.
  * **aggfunc** (*function* *,* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *functions* *,* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *,* *default numpy.mean*) – If list of functions passed, the resulting pivot table will have
    hierarchical columns whose top level are the function names
    (inferred from the function objects themselves)
    If dict is passed, the key is column to aggregate and value
    is function or list of functions.
  * **fill_value** (*scalar* *,* *default None*) – Value to replace missing values with (in the resulting pivot table,
    after aggregation).
  * **margins** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Add all row / columns (e.g. for subtotal / grand totals).
  * **dropna** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Do not include columns whose entries are all NaN.
  * **margins_name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default 'All'*) – Name of the row / column that will contain the totals
    when margins is True.
  * **sort** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Specifies if the result should be sorted.
* **Returns:**
  An Excel style pivot table.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.pivot`](maxframe.dataframe.DataFrame.pivot.md#maxframe.dataframe.DataFrame.pivot)
: Pivot without aggregation that can handle non-numeric data.

[`DataFrame.melt`](maxframe.dataframe.DataFrame.melt.md#maxframe.dataframe.DataFrame.melt)
: Unpivot a DataFrame from wide to long format, optionally leaving identifiers set.

`wide_to_long`
: Wide panel to long format. Less flexible but more user-friendly than melt.

### Examples

```pycon
>>> import numpy as np
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({"A": ["foo", "foo", "foo", "foo", "foo",
...                          "bar", "bar", "bar", "bar"],
...                    "B": ["one", "one", "one", "two", "two",
...                          "one", "one", "two", "two"],
...                    "C": ["small", "large", "large", "small",
...                          "small", "large", "small", "small",
...                          "large"],
...                    "D": [1, 2, 2, 3, 3, 4, 5, 6, 7],
...                    "E": [2, 4, 5, 5, 6, 6, 8, 9, 9]})
>>> df.execute()
     A    B      C  D  E
0  foo  one  small  1  2
1  foo  one  large  2  4
2  foo  one  large  2  5
3  foo  two  small  3  5
4  foo  two  small  3  6
5  bar  one  large  4  6
6  bar  one  small  5  8
7  bar  two  small  6  9
8  bar  two  large  7  9
```

This first example aggregates values by taking the sum.

```pycon
>>> table = md.pivot_table(df, values='D', index=['A', 'B'],
...                        columns=['C'], aggfunc=np.sum)
>>> table.execute()
C        large  small
A   B
bar one    4.0    5.0
    two    7.0    6.0
foo one    4.0    1.0
    two    NaN    6.0
```

We can also fill missing values using the fill_value parameter.

```pycon
>>> table = md.pivot_table(df, values='D', index=['A', 'B'],
...                        columns=['C'], aggfunc=np.sum, fill_value=0)
>>> table.execute()
C        large  small
A   B
bar one      4      5
    two      7      6
foo one      4      1
    two      0      6
```

The next example aggregates by taking the mean across multiple columns.

```pycon
>>> table = md.pivot_table(df, values=['D', 'E'], index=['A', 'C'],
...                        aggfunc={'D': np.mean,
...                                 'E': np.mean})
>>> table.execute()
                D         E
A   C
bar large  5.500000  7.500000
    small  5.500000  8.500000
foo large  2.000000  4.500000
    small  2.333333  4.333333
```

We can also calculate multiple types of aggregations for any given
value column.

```pycon
>>> table = md.pivot_table(df, values=['D', 'E'], index=['A', 'C'],
...                        aggfunc={'D': np.mean,
...                                 'E': [min, max, np.mean]})
>>> table.execute()
                D    E
            mean  max      mean  min
A   C
bar large  5.500000  9.0  7.500000  6.0
    small  5.500000  9.0  8.500000  8.0
foo large  2.000000  5.0  4.500000  4.0
    small  2.333333  6.0  4.333333  2.0
```
