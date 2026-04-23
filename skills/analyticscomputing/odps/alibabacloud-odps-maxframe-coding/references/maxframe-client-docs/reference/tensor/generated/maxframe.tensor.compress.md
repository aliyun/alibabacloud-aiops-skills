# maxframe.tensor.compress

### maxframe.tensor.compress(condition, a, axis=None, out=None)

Return selected slices of a tensor along given axis.

When working along a given axis, a slice along that axis is returned in
output for each index where condition evaluates to True. When
working on a 1-D array, compress is equivalent to extract.

* **Parameters:**
  * **condition** (*1-D tensor* *of* *bools*) – Tensor that selects which entries to return. If len(condition)
    is less than the size of a along the given axis, then output is
    truncated to the length of the condition tensor.
  * **a** (*array_like*) – Tensor from which to extract a part.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which to take slices. If None (default), work on the
    flattened tensor.
  * **out** (*Tensor* *,* *optional*) – Output tensor.  Its type is preserved and it must be of the right
    shape to hold the output.
* **Returns:**
  **compressed_array** – A copy of a without the slices along axis for which condition
  is false.
* **Return type:**
  Tensor

#### SEE ALSO
[`take`](maxframe.tensor.take.md#maxframe.tensor.take), [`choose`](maxframe.tensor.choose.md#maxframe.tensor.choose), [`diag`](maxframe.tensor.diag.md#maxframe.tensor.diag), `diagonal`, [`select`](https://docs.python.org/3/library/select.html#module-select)

`Tensor.compress`
: Equivalent method in ndarray

`mt.extract`
: Equivalent method when working on 1-D arrays

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([[1, 2], [3, 4], [5, 6]])
>>> a.execute()
array([[1, 2],
       [3, 4],
       [5, 6]])
>>> mt.compress([0, 1], a, axis=0).execute()
array([[3, 4]])
>>> mt.compress([False, True, True], a, axis=0).execute()
array([[3, 4],
       [5, 6]])
>>> mt.compress([False, True], a, axis=1).execute()
array([[2],
       [4],
       [6]])
```

Working on the flattened tensor does not return slices along an axis but
selects elements.

```pycon
>>> mt.compress([False, True], a).execute()
array([2])
```
