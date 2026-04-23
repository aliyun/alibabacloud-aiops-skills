# maxframe.tensor.bitwise_or

### maxframe.tensor.bitwise_or(x1, x2, out=None, where=None, \*\*kwargs)

Compute the bit-wise OR of two tensors element-wise.

Computes the bit-wise OR of the underlying binary representation of
the integers in the input arrays. This ufunc implements the C/Python
operator `|`.

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
[`logical_or`](maxframe.tensor.logical_or.md#maxframe.tensor.logical_or), [`bitwise_and`](maxframe.tensor.bitwise_and.md#maxframe.tensor.bitwise_and), [`bitwise_xor`](maxframe.tensor.bitwise_xor.md#maxframe.tensor.bitwise_xor)

`binary_repr`
: Return the binary representation of the input number as a string.

### Examples

The number 13 has the binaray representation `00001101`. Likewise,
16 is represented by `00010000`.  The bit-wise OR of 13 and 16 is
then `000111011`, or 29:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.bitwise_or(13, 16).execute()
29
```

```pycon
>>> mt.bitwise_or(32, 2).execute()
34
>>> mt.bitwise_or([33, 4], 1).execute()
array([33,  5])
>>> mt.bitwise_or([33, 4], [1, 2]).execute()
array([33,  6])
```

```pycon
>>> mt.bitwise_or(mt.array([2, 5, 255]), mt.array([4, 4, 4])).execute()
array([  6,   5, 255])
>>> (mt.array([2, 5, 255]) | mt.array([4, 4, 4])).execute()
array([  6,   5, 255])
>>> mt.bitwise_or(mt.array([2, 5, 255, 2147483647], dtype=mt.int32),
...               mt.array([4, 4, 4, 2147483647], dtype=mt.int32)).execute()
array([         6,          5,        255, 2147483647])
>>> mt.bitwise_or([True, True], [False, True]).execute()
array([ True,  True])
```
