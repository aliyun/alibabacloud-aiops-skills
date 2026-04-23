# maxframe.dataframe.Series.ndim

#### *property* Series.ndim

Return an int representing the number of axes / array dimensions.

Return 1 if Series. Otherwise return 2 if DataFrame.

#### SEE ALSO
`ndarray.ndim`
: Number of array dimensions.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series({'a': 1, 'b': 2, 'c': 3})
>>> s.ndim
1
```

```pycon
>>> df = md.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
>>> df.ndim
2
```
