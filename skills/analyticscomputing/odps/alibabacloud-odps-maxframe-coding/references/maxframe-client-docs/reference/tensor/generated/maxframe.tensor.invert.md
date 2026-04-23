# maxframe.tensor.invert

### maxframe.tensor.invert(x, out=None, where=None, \*\*kwargs)

Compute bit-wise inversion, or bit-wise NOT, element-wise.

Computes the bit-wise NOT of the underlying binary representation of
the integers in the input tensors. This ufunc implements the C/Python
operator `~`.

For signed integer inputs, the two’s complement is returned.  In a
two’s-complement system negative numbers are represented by the two’s
complement of the absolute value. This is the most common method of
representing signed integers on computers <sup>[1](#id2)</sup>. A N-bit
two’s-complement system can represent every integer in the range
$-2^{N-1}$ to $+2^{N-1}-1$.

* **Parameters:**
  * **x** (*array_like*) – Only integer and boolean types are handled.
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
[`bitwise_and`](maxframe.tensor.bitwise_and.md#maxframe.tensor.bitwise_and), [`bitwise_or`](maxframe.tensor.bitwise_or.md#maxframe.tensor.bitwise_or), [`bitwise_xor`](maxframe.tensor.bitwise_xor.md#maxframe.tensor.bitwise_xor), [`logical_not`](maxframe.tensor.logical_not.md#maxframe.tensor.logical_not)

### Notes

bitwise_not is an alias for invert:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.bitwise_not is mt.invert
True
```

### References

* <a id='id2'>**[1]**</a> Wikipedia, “Two’s complement”, [http://en.wikipedia.org/wiki/Two’s_complement](http://en.wikipedia.org/wiki/Two's_complement)

### Examples

We’ve seen that 13 is represented by `00001101`.
The invert or bit-wise NOT of 13 is then:

```pycon
>>> mt.invert(mt.array([13], dtype=mt.uint8)).execute()
array([242], dtype=uint8)
```

The result depends on the bit-width:

```pycon
>>> mt.invert(mt.array([13], dtype=mt.uint16)).execute()
array([65522], dtype=uint16)
```

When using signed integer types the result is the two’s complement of
the result for the unsigned type:

```pycon
>>> mt.invert(mt.array([13], dtype=mt.int8)).execute()
array([-14], dtype=int8)
```

Booleans are accepted as well:

```pycon
>>> mt.invert(mt.array([True, False])).execute()
array([False,  True])
```
