# maxframe.dataframe.Series.repeat

#### Series.repeat(repeats, axis=None)

Repeat elements of a Series.

Returns a new Series where each element of the current Series
is repeated consecutively a given number of times.

* **Parameters:**
  * **repeats** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *array* *of* *ints*) – The number of repetitions for each element. This should be a
    non-negative integer. Repeating 0 times will return an empty
    Series.
  * **axis** (*None*) – Must be `None`. Has no effect but is accepted for compatibility
    with numpy.
* **Returns:**
  Newly created Series with repeated elements.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Index.repeat`](maxframe.dataframe.Index.repeat.md#maxframe.dataframe.Index.repeat)
: Equivalent function for Index.

[`numpy.repeat`](https://numpy.org/doc/stable/reference/generated/numpy.repeat.html#numpy.repeat)
: Similar method for [`numpy.ndarray`](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html#numpy.ndarray).

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(['a', 'b', 'c'])
>>> s.execute()
0    a
1    b
2    c
dtype: object
>>> s.repeat(2).execute()
0    a
0    a
1    b
1    b
2    c
2    c
dtype: object
>>> s.repeat([1, 2, 3]).execute()
0    a
1    b
1    b
2    c
2    c
2    c
dtype: object
```
