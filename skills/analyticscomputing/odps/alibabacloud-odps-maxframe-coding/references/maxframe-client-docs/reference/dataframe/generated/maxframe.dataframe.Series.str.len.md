# maxframe.dataframe.Series.str.len

#### Series.str.len()

Compute the length of each element in the Series/Index.

The element may be a sequence (such as a string, tuple or list) or a collection
(such as a dictionary).

* **Returns:**
  A Series or Index of integer values indicating the length of each
  element in the Series or Index.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index) of [int](https://docs.python.org/3/library/functions.html#int)

#### SEE ALSO
`str.len`
: Python built-in function returning the length of an object.

`Series.size`
: Returns the length of the Series.

### Examples

Returns the length (number of characters) in a string. Returns the
number of entries for dictionaries, lists or tuples.

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(['dog',
...                 '',
...                 5,
...                 {'foo' : 'bar'},
...                 [2, 3, 5, 7],
...                 ('one', 'two', 'three')])
>>> s.execute()
0                  dog
1
2                    5
3       {'foo': 'bar'}
4         [2, 3, 5, 7]
5    (one, two, three)
dtype: object
>>> s.str.len().execute()
0    3.0
1    0.0
2    NaN
3    1.0
4    4.0
5    3.0
dtype: float64
```
