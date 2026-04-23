# maxframe.dataframe.Series.agg

#### Series.agg(func=None, axis=0, \*\*kw)

Aggregate using one or more operations over the specified axis.

* **Parameters:**
  * **df** ([*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) *,* [*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – Object to aggregate.
  * **func** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *or* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict)) – Function to use for aggregating the data.
  * **axis** ( *{0* *or*  *‘index’* *,* *1* *or*  *‘columns’}* *,* *default 0*) – If 0 or ‘index’: apply function to each column. If 1 or ‘columns’: apply function to each row.
  * **kw** – Keyword arguments to pass to func.
* **Returns:**
  The return can be:
  * scalar : when Series.agg is called with single function
  * Series : when DataFrame.agg is called with a single function
  * DataFrame : when DataFrame.agg is called with several functions
* **Return type:**
  scalar, [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([[1, 2, 3],
...            [4, 5, 6],
...            [7, 8, 9],
...            [np.nan, np.nan, np.nan]],
...           columns=['A', 'B', 'C']).execute()
```

Aggregate these functions over the rows.

```pycon
>>> df.agg(['sum', 'min']).execute()
        A     B     C
min   1.0   2.0   3.0
sum  12.0  15.0  18.0
```

Different aggregations per column.

```pycon
>>> df.agg({'A' : ['sum', 'min'], 'B' : ['min', 'max']}).execute()
        A    B
max   NaN  8.0
min   1.0  2.0
sum  12.0  NaN
```

Aggregate different functions over the columns and rename the index of the resulting DataFrame.

```pycon
>>> df.agg(x=('A', 'max'), y=('B', 'min'), z=('C', 'mean')).execute()
     A    B    C
x  7.0  NaN  NaN
y  NaN  2.0  NaN
z  NaN  NaN  6.0
```

```pycon
>>> s = md.Series([1, 2, 3, 4])
>>> s.agg('min').execute()
1
```

```pycon
>>> s.agg(['min', 'max']).execute()
max    4
min    1
```
