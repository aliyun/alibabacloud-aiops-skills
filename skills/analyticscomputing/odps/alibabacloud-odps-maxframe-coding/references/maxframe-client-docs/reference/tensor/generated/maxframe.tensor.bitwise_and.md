# maxframe.tensor.bitwise_and

### maxframe.tensor.bitwise_and(x1, x2, out=None, where=None, \*\*kwargs)

Compute the bit-wise AND of two tensors element-wise.

Computes the bit-wise AND of the underlying binary representation of
the integers in the input arrays. This ufunc implements the C/Python
operator `&`.

* **Parameters:**
  * **x1** (*array_like*) – Only integer and boolean types are handled.
  * **x2** (*array_like*) – Only integer and boolean types are handled.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **out** – Result.
* **Return type:**
  array_like

#### SEE ALSO
[`logical_and`](maxframe.tensor.logical_and.md#maxframe.tensor.logical_and), [`bitwise_or`](maxframe.tensor.bitwise_or.md#maxframe.tensor.bitwise_or), [`bitwise_xor`](maxframe.tensor.bitwise_xor.md#maxframe.tensor.bitwise_xor)

### Examples

The number 13 is represented by `00001101`.  Likewise, 17 is
represented by `00010001`.  The bit-wise AND of 13 and 17 is
therefore `000000001`, or 1:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.bitwise_and(13, 17).execute()
1
```

```pycon
>>> mt.bitwise_and(14, 13).execute()
12
>>> mt.bitwise_and([14,3], 13).execute()
array([12,  1])
```

```pycon
>>> mt.bitwise_and([11,7], [4,25]).execute()
array([0, 1])
>>> mt.bitwise_and(mt.array([2,5,255]), mt.array([3,14,16])).execute()
array([ 2,  4, 16])
>>> mt.bitwise_and([True, True], [False, True]).execute()
array([False,  True])
```
