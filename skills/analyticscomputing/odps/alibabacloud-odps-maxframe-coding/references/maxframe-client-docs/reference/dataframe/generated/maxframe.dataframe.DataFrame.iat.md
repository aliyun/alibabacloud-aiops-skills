# maxframe.dataframe.DataFrame.iat

#### *property* DataFrame.iat

Access a single value for a row/column pair by integer position.

Similar to `iloc`, in that both provide integer-based lookups. Use
`iat` if you only need to get or set a single value in a DataFrame
or Series.

* **Raises:**
  [**IndexError**](https://docs.python.org/3/library/exceptions.html#IndexError) – When integer position is out of bounds.

#### SEE ALSO
[`DataFrame.at`](maxframe.dataframe.DataFrame.at.md#maxframe.dataframe.DataFrame.at)
: Access a single value for a row/column label pair.

[`DataFrame.loc`](maxframe.dataframe.DataFrame.loc.md#maxframe.dataframe.DataFrame.loc)
: Access a group of rows and columns by label(s).

[`DataFrame.iloc`](maxframe.dataframe.DataFrame.iloc.md#maxframe.dataframe.DataFrame.iloc)
: Access a group of rows and columns by integer position(s).

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([[0, 2, 3], [0, 4, 1], [10, 20, 30]],
...                   columns=['A', 'B', 'C'])
>>> df.execute()
    A   B   C
0   0   2   3
1   0   4   1
2  10  20  30
```

Get value at specified row/column pair

```pycon
>>> df.iat[1, 2].execute()
1
```

Set value at specified row/column pair

```pycon
>>> df.iat[1, 2] = 10
>>> df.iat[1, 2].execute()
10
```

Get value within a series

```pycon
>>> df.loc[0].iat[1].execute()
2
```
