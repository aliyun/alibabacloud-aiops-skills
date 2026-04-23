# maxframe.tensor.ldexp

### maxframe.tensor.ldexp(x1, x2, out=None, where=None, \*\*kwargs)

Returns x1 \* 2\*\*x2, element-wise.

The mantissas x1 and twos exponents x2 are used to construct
floating point numbers `x1 * 2**x2`.

* **Parameters:**
  * **x1** (*array_like*) – Tensor of multipliers.
  * **x2** (*array_like* *,* [*int*](https://docs.python.org/3/library/functions.html#int)) – Tensor of twos exponents.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The result of `x1 * 2**x2`.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`frexp`](maxframe.tensor.frexp.md#maxframe.tensor.frexp)
: Return (y1, y2) from `x = y1 * 2**y2`, inverse to ldexp.

### Notes

Complex dtypes are not supported, they will raise a TypeError.

ldexp is useful as the inverse of frexp, if used by itself it is
more clear to simply use the expression `x1 * 2**x2`.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.ldexp(5, mt.arange(4)).execute()
array([  5.,  10.,  20.,  40.], dtype=float32)
```

```pycon
>>> x = mt.arange(6)
>>> mt.ldexp(*mt.frexp(x)).execute()
array([ 0.,  1.,  2.,  3.,  4.,  5.])
```
