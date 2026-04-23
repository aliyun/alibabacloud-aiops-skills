# maxframe.tensor.isnan

### maxframe.tensor.isnan(x, out=None, where=None, \*\*kwargs)

Test element-wise for NaN and return result as a boolean tensor.

* **Parameters:**
  * **x** (*array_like*) – Input tensor.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – For scalar input, the result is a new boolean with value True if
  the input is NaN; otherwise the value is False.

  For array input, the result is a boolean tensor of the same
  dimensions as the input and the values are True if the
  corresponding element of the input is NaN; otherwise the values are
  False.
* **Return type:**
  Tensor or [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`isinf`](maxframe.tensor.isinf.md#maxframe.tensor.isinf), `isneginf`, `isposinf`, [`isfinite`](maxframe.tensor.isfinite.md#maxframe.tensor.isfinite), `isnat`

### Notes

MaxFrame uses the IEEE Standard for Binary Floating-Point for Arithmetic
(IEEE 754). This means that Not a Number is not equivalent to infinity.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.isnan(mt.nan).execute()
True
>>> mt.isnan(mt.inf).execute()
False
>>> mt.isnan([mt.log(-1.).execute(),1.,mt.log(0).execute()]).execute()
array([ True, False, False])
```
