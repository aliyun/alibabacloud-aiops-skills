# maxframe.tensor.delete

### maxframe.tensor.delete(arr, obj, axis=None)

Return a new array with sub-arrays along an axis deleted. For a one
dimensional array, this returns those entries not returned by
arr[obj].

* **Parameters:**
  * **arr** (*array_like*) – Input array.
  * **obj** ([*slice*](https://docs.python.org/3/library/functions.html#slice) *,* [*int*](https://docs.python.org/3/library/functions.html#int) *or* *array* *of* *ints*) – Indicate indices of sub-arrays to remove along the specified axis.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The axis along which to delete the subarray defined by obj.
    If axis is None, obj is applied to the flattened array.
* **Returns:**
  **out** – A copy of arr with the elements specified by obj removed. Note
  that delete does not occur in-place. If axis is None, out is
  a flattened array.
* **Return type:**
  maxframe.tensor.Tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> arr = mt.array([[1,2,3,4], [5,6,7,8], [9,10,11,12]])
>>> arr.execute()
array([[ 1,  2,  3,  4],
       [ 5,  6,  7,  8],
       [ 9, 10, 11, 12]])
>>> mt.delete(arr, 1, 0).execute()
array([[ 1,  2,  3,  4],
       [ 9, 10, 11, 12]])
>>> mt.delete(arr, np.s_[::2], 1).execute()
array([[ 2,  4],
       [ 6,  8],
       [10, 12]])
>>> mt.delete(arr, [1,3,5], None).execute()
array([ 1,  3,  5,  7,  8,  9, 10, 11, 12])
```
