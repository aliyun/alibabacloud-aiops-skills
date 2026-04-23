# maxframe.tensor.insert

### maxframe.tensor.insert(arr, obj, values, axis=None)

Insert values along the given axis before the given indices.

* **Parameters:**
  * **arr** (*array like*) – Input array.
  * **obj** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*slice*](https://docs.python.org/3/library/functions.html#slice) *or* *sequence* *of* *ints*) – Object that defines the index or indices before which values is
    inserted.
  * **values** (*array_like*) – Values to insert into arr. If the type of values is different
    from that of arr, values is converted to the type of arr.
    values should be shaped so that `arr[...,obj,...] = values`
    is legal.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which to insert values.  If axis is None then arr
    is flattened first.
* **Returns:**
  **out** – A copy of arr with values inserted.  Note that insert
  does not occur in-place: a new array is returned. If
  axis is None, out is a flattened array.
* **Return type:**
  ndarray

#### SEE ALSO
`append`
: Append elements at the end of an array.

[`concatenate`](maxframe.tensor.concatenate.md#maxframe.tensor.concatenate)
: Join a sequence of arrays along an existing axis.

[`delete`](maxframe.tensor.delete.md#maxframe.tensor.delete)
: Delete elements from an array.

### Notes

Note that for higher dimensional inserts obj=0 behaves very different
from obj=[0] just like arr[:,0,:] = values is different from
arr[:,[0],:] = values.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> a = mt.array([[1, 1], [2, 2], [3, 3]])
>>> a.execute()
array([[1, 1],
       [2, 2],
       [3, 3]])
>>> mt.insert(a, 1, 5).execute()
array([1, 5, 1, ..., 2, 3, 3])
>>> mt.insert(a, 1, 5, axis=1).execute()
array([[1, 5, 1],
       [2, 5, 2],
       [3, 5, 3]])
Difference between sequence and scalars:
>>> mt.insert(a, [1], [[1],[2],[3]], axis=1).execute()
array([[1, 1, 1],
       [2, 2, 2],
       [3, 3, 3]])
>>> b = a.flatten()
>>> b.execute()
array([1, 1, 2, 2, 3, 3])
>>> mt.insert(b, [2, 2], [5, 6]).execute()
array([1, 1, 5, ..., 2, 3, 3])
>>> mt.insert(b, slice(2, 4), [5, 6]).execute()
array([1, 1, 5, ..., 2, 3, 3])
>>> mt.insert(b, [2, 2], [7.13, False]).execute() # type casting
array([1, 1, 7, ..., 2, 3, 3])
>>> x = mt.arange(8).reshape(2, 4)
>>> idx = (1, 3)
>>> mt.insert(x, idx, 999, axis=1).execute()
array([[  0, 999,   1,   2, 999,   3],
       [  4, 999,   5,   6, 999,   7]])
```
