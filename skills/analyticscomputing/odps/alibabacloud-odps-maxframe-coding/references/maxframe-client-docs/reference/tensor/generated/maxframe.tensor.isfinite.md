# maxframe.tensor.isfinite

### maxframe.tensor.isfinite(x, out=None, where=None, \*\*kwargs)

Test element-wise for finiteness (not infinity or not Not a Number).

The result is returned as a boolean tensor.

* **Parameters:**
  * **x** (*array_like*) – Input values.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – For scalar input, the result is a new boolean with value True
  if the input is finite; otherwise the value is False (input is
  either positive infinity, negative infinity or Not a Number).

  For array input, the result is a boolean array with the same
  dimensions as the input and the values are True if the
  corresponding element of the input is finite; otherwise the values
  are False (element is either positive infinity, negative infinity
  or Not a Number).
* **Return type:**
  Tensor, [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`isinf`](maxframe.tensor.isinf.md#maxframe.tensor.isinf), `isneginf`, `isposinf`, [`isnan`](maxframe.tensor.isnan.md#maxframe.tensor.isnan)

### Notes

Not a Number, positive infinity and negative infinity are considered
to be non-finite.

MaxFrame uses the IEEE Standard for Binary Floating-Point for Arithmetic
(IEEE 754). This means that Not a Number is not equivalent to infinity.
Also that positive infinity is not equivalent to negative infinity. But
infinity is equivalent to positive infinity.  Errors result if the
second argument is also supplied when x is a scalar input, or if
first and second arguments have different shapes.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.isfinite(1).execute()
True
>>> mt.isfinite(0).execute()
True
>>> mt.isfinite(mt.nan).execute()
False
>>> mt.isfinite(mt.inf).execute()
False
>>> mt.isfinite(mt.NINF).execute()
False
>>> mt.isfinite([mt.log(-1.).execute(),1.,mt.log(0).execute()]).execute()
array([False,  True, False])
```

```pycon
>>> x = mt.array([-mt.inf, 0., mt.inf])
>>> y = mt.array([2, 2, 2])
>>> mt.isfinite(x, y).execute()
array([0, 1, 0])
>>> y.execute()
array([0, 1, 0])
```
