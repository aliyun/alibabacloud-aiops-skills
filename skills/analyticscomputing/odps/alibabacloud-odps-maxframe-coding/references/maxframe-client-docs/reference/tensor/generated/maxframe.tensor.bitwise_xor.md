# maxframe.tensor.bitwise_xor

### maxframe.tensor.bitwise_xor(x1, x2, out=None, where=None, \*\*kwargs)

Compute the bit-wise XOR of two arrays element-wise.

Computes the bit-wise XOR of the underlying binary representation of
the integers in the input arrays. This ufunc implements the C/Python
operator `^`.

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
[`logical_xor`](maxframe.tensor.logical_xor.md#maxframe.tensor.logical_xor), [`bitwise_and`](maxframe.tensor.bitwise_and.md#maxframe.tensor.bitwise_and), [`bitwise_or`](maxframe.tensor.bitwise_or.md#maxframe.tensor.bitwise_or)

`binary_repr`
: Return the binary representation of the input number as a string.

### Examples

The number 13 is represented by `00001101`. Likewise, 17 is
represented by `00010001`.  The bit-wise XOR of 13 and 17 is
therefore `00011100`, or 28:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.bitwise_xor(13, 17).execute()
28
```

```pycon
>>> mt.bitwise_xor(31, 5).execute()
26
>>> mt.bitwise_xor([31,3], 5).execute()
array([26,  6])
```

```pycon
>>> mt.bitwise_xor([31,3], [5,6]).execute()
array([26,  5])
>>> mt.bitwise_xor([True, True], [False, True]).execute()
array([ True, False])
```
