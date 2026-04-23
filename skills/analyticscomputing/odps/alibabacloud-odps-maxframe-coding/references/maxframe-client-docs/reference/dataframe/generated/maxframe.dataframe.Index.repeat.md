# maxframe.dataframe.Index.repeat

#### Index.repeat(repeats, axis=None)

Repeat elements of an Index.

Returns a new Index where each element of the current Index
is repeated consecutively a given number of times.

* **Parameters:**
  * **repeats** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *array* *of* *ints*) – The number of repetitions for each element. This should be a
    non-negative integer. Repeating 0 times will return an empty
    Index.
  * **axis** (*None*) – Must be `None`. Has no effect but is accepted for compatibility
    with numpy.
* **Returns:**
  **repeated_index** – Newly created Index with repeated elements.
* **Return type:**
  [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

#### SEE ALSO
[`Series.repeat`](maxframe.dataframe.Series.repeat.md#maxframe.dataframe.Series.repeat)
: Equivalent function for Series.

[`numpy.repeat`](https://numpy.org/doc/stable/reference/generated/numpy.repeat.html#numpy.repeat)
: Similar method for [`numpy.ndarray`](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html#numpy.ndarray).

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> idx = md.Index(['a', 'b', 'c'])
>>> idx.execute()
Index(['a', 'b', 'c'], dtype='object')
>>> idx.repeat(2).execute()
Index(['a', 'a', 'b', 'b', 'c', 'c'], dtype='object')
>>> idx.repeat([1, 2, 3]).execute()
Index(['a', 'b', 'b', 'c', 'c', 'c'], dtype='object')
```
