# maxframe.tensor.frexp

### maxframe.tensor.frexp(x, out1=None, out2=None, out=None, where=None, \*\*kwargs)

Decompose the elements of x into mantissa and twos exponent.

Returns (mantissa, exponent), where x = mantissa \* 2\*\*exponent\`.
The mantissa is lies in the open interval(-1, 1), while the twos
exponent is a signed integer.

* **Parameters:**
  * **x** (*array_like*) – Tensor of numbers to be decomposed.
  * **out1** (*Tensor* *,* *optional*) – Output tensor for the mantissa. Must have the same shape as x.
  * **out2** (*Tensor* *,* *optional*) – Output tensor for the exponent. Must have the same shape as x.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **(mantissa, exponent)** – mantissa is a float array with values between -1 and 1.
  exponent is an int array which represents the exponent of 2.
* **Return type:**
  [tuple](https://docs.python.org/3/library/stdtypes.html#tuple) of tensors, ([float](https://docs.python.org/3/library/functions.html#float), [int](https://docs.python.org/3/library/functions.html#int))

#### SEE ALSO
[`ldexp`](maxframe.tensor.ldexp.md#maxframe.tensor.ldexp)
: Compute `y = x1 * 2**x2`, the inverse of frexp.

### Notes

Complex dtypes are not supported, they will raise a TypeError.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.arange(9)
>>> y1, y2 = mt.frexp(x)
```

```pycon
>>> y1_result, y2_result = mt.ExecutableTuple([y1, y2]).execute()
>>> y1_result
array([ 0.   ,  0.5  ,  0.5  ,  0.75 ,  0.5  ,  0.625,  0.75 ,  0.875,
        0.5  ])
>>> y2_result
array([0, 1, 2, 2, 3, 3, 3, 3, 4])
>>> (y1 * 2**y2).execute()
array([ 0.,  1.,  2.,  3.,  4.,  5.,  6.,  7.,  8.])
```
