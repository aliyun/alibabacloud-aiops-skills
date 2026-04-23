# maxframe.dataframe.DataFrame.at

#### *property* DataFrame.at

Access a single value for a row/column label pair.

Similar to `loc`, in that both provide label-based lookups. Use
`at` if you only need to get or set a single value in a DataFrame
or Series.

* **Raises:**
  [**KeyError**](https://docs.python.org/3/library/exceptions.html#KeyError) – If ‘label’ does not exist in DataFrame.

#### SEE ALSO
[`DataFrame.iat`](maxframe.dataframe.DataFrame.iat.md#maxframe.dataframe.DataFrame.iat)
: Access a single value for a row/column pair by integer position.

[`DataFrame.loc`](maxframe.dataframe.DataFrame.loc.md#maxframe.dataframe.DataFrame.loc)
: Access a group of rows and columns by label(s).

[`Series.at`](maxframe.dataframe.Series.at.md#maxframe.dataframe.Series.at)
: Access a single value using a label.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([[0, 2, 3], [0, 4, 1], [10, 20, 30]],
...                   index=[4, 5, 6], columns=['A', 'B', 'C'])
>>> df.execute()
    A   B   C
4   0   2   3
5   0   4   1
6  10  20  30
```

Get value at specified row/column pair

```pycon
>>> df.at[4, 'B'].execute()
2
```

# Set value at specified row/column pair
#
# >>> df.at[4, ‘B’] = 10
# >>> df.at[4, ‘B’]
# 10

Get value within a Series

```pycon
>>> df.loc[5].at['B'].execute()
4
```
