# maxframe.tensor.fmod

### maxframe.tensor.fmod(x1, x2, out=None, where=None, \*\*kwargs)

Return the element-wise remainder of division.

This is the NumPy implementation of the C library function fmod, the
remainder has the same sign as the dividend x1. It is equivalent to
the Matlab(TM) `rem` function and should not be confused with the
Python modulus operator `x1 % x2`.

* **Parameters:**
  * **x1** (*array_like*) – Dividend.
  * **x2** (*array_like*) – Divisor.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs** – For other keyword-only arguments, see the
    [ufunc docs](https://numpy.org/doc/stable/reference/ufuncs.html#ufuncs-kwargs).
* **Returns:**
  **y** – The remainder of the division of x1 by x2.
* **Return type:**
  Tensor_like

#### SEE ALSO
[`remainder`](maxframe.tensor.remainder.md#maxframe.tensor.remainder)
: Equivalent to the Python `%` operator.

[`divide`](maxframe.tensor.divide.md#maxframe.tensor.divide)

### Notes

The result of the modulo operation for negative dividend and divisors
is bound by conventions. For fmod, the sign of result is the sign of
the dividend, while for remainder the sign of the result is the sign
of the divisor. The fmod function is equivalent to the Matlab(TM)
`rem` function.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.fmod([-3, -2, -1, 1, 2, 3], 2).execute()
array([-1,  0, -1,  1,  0,  1])
>>> mt.remainder([-3, -2, -1, 1, 2, 3], 2).execute()
array([1, 0, 1, 1, 0, 1])
```

```pycon
>>> mt.fmod([5, 3], [2, 2.]).execute()
array([ 1.,  1.])
>>> a = mt.arange(-3, 3).reshape(3, 2)
>>> a.execute()
array([[-3, -2],
       [-1,  0],
       [ 1,  2]])
>>> mt.fmod(a, [2,2]).execute()
array([[-1,  0],
       [-1,  0],
       [ 1,  0]])
```
