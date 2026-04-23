# maxframe.tensor.isinf

### maxframe.tensor.isinf(x, out=None, where=None, \*\*kwargs)

Test element-wise for positive or negative infinity.

Returns a boolean array of the same shape as x, True where `x ==
+/-inf`, otherwise False.

* **Parameters:**
  * **x** (*array_like*) – Input values
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – For scalar input, the result is a new boolean with value True if
  the input is positive or negative infinity; otherwise the value is
  False.

  For tensor input, the result is a boolean tensor with the same shape
  as the input and the values are True where the corresponding
  element of the input is positive or negative infinity; elsewhere
  the values are False.  If a second argument was supplied the result
  is stored there.  If the type of that array is a numeric type the
  result is represented as zeros and ones, if the type is boolean
  then as False and True, respectively.  The return value y is then
  a reference to that tensor.
* **Return type:**
  [bool](https://docs.python.org/3/library/functions.html#bool) (scalar) or boolean Tensor

#### SEE ALSO
`isneginf`, `isposinf`, [`isnan`](maxframe.tensor.isnan.md#maxframe.tensor.isnan), [`isfinite`](maxframe.tensor.isfinite.md#maxframe.tensor.isfinite)

### Notes

MaxFrame uses the IEEE Standard for Binary Floating-Point for Arithmetic
(IEEE 754).

Errors result if the second argument is supplied when the first
argument is a scalar, or if the first and second arguments have
different shapes.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.isinf(mt.inf).execute()
True
>>> mt.isinf(mt.nan).execute()
False
>>> mt.isinf(mt.NINF).execute()
True
>>> mt.isinf([mt.inf, -mt.inf, 1.0, mt.nan]).execute()
array([ True,  True, False, False])
```

```pycon
>>> x = mt.array([-mt.inf, 0., mt.inf])
>>> y = mt.array([2, 2, 2])
>>> mt.isinf(x, y).execute()
array([1, 0, 1])
>>> y.execute()
array([1, 0, 1])
```
