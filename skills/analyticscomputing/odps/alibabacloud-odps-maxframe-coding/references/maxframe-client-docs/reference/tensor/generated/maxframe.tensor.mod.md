# maxframe.tensor.mod

### maxframe.tensor.mod(x1, x2, out=None, where=None, \*\*kwargs)

Return element-wise remainder of division.

Computes the remainder complementary to the floor_divide function.  It is
equivalent to the Python modulus operator\`\`x1 % x2\`\` and has the same sign
as the divisor x2. The MATLAB function equivalent to `np.remainder`
is `mod`.

#### WARNING
This should not be confused with:

* Python 3.7’s math.remainder and C’s `remainder`, which
  computes the IEEE remainder, which are the complement to
  `round(x1 / x2)`.
* The MATLAB `rem` function and or the C `%` operator which is the
  complement to `int(x1 / x2)`.

* **Parameters:**
  * **x1** (*array_like*) – Dividend array.
  * **x2** (*array_like*) – Divisor array.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The element-wise remainder of the quotient `floor_divide(x1, x2)`.
  Returns a scalar if both  x1 and x2 are scalars.
* **Return type:**
  Tensor

#### SEE ALSO
[`floor_divide`](maxframe.tensor.floor_divide.md#maxframe.tensor.floor_divide)
: Equivalent of Python `//` operator.

[`divmod`](https://docs.python.org/3/library/functions.html#divmod)
: Simultaneous floor division and remainder.

[`fmod`](maxframe.tensor.fmod.md#maxframe.tensor.fmod)
: Equivalent of the MATLAB `rem` function.

[`divide`](maxframe.tensor.divide.md#maxframe.tensor.divide), [`floor`](maxframe.tensor.floor.md#maxframe.tensor.floor)

### Notes

Returns 0 when x2 is 0 and both x1 and x2 are (tensors of)
integers.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.remainder([4, 7], [2, 3]).execute()
array([0, 1])
>>> mt.remainder(mt.arange(7), 5).execute()
array([0, 1, 2, 3, 4, 0, 1])
```
