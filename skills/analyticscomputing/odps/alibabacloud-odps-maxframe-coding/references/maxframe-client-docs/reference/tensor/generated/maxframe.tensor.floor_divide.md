# maxframe.tensor.floor_divide

### maxframe.tensor.floor_divide(x1, x2, out=None, where=None, \*\*kwargs)

Return the largest integer smaller or equal to the division of the inputs.
It is equivalent to the Python `//` operator and pairs with the
Python `%` (remainder), function so that `b = a % b + b * (a // b)`
up to roundoff.

* **Parameters:**
  * **x1** (*array_like*) – Numerator.
  * **x2** (*array_like*) – Denominator.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated array is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – y = floor(x1/x2)
* **Return type:**
  Tensor

#### SEE ALSO
[`remainder`](maxframe.tensor.remainder.md#maxframe.tensor.remainder)
: Remainder complementary to floor_divide.

[`divmod`](https://docs.python.org/3/library/functions.html#divmod)
: Simultaneous floor division and remainder.

[`divide`](maxframe.tensor.divide.md#maxframe.tensor.divide)
: Standard division.

[`floor`](maxframe.tensor.floor.md#maxframe.tensor.floor)
: Round a number to the nearest integer toward minus infinity.

[`ceil`](maxframe.tensor.ceil.md#maxframe.tensor.ceil)
: Round a number to the nearest integer toward infinity.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.floor_divide(7,3).execute()
2
>>> mt.floor_divide([1., 2., 3., 4.], 2.5).execute()
array([ 0.,  0.,  1.,  1.])
```
