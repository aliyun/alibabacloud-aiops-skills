# maxframe.tensor.modf

### maxframe.tensor.modf(x, out1=None, out2=None, out=None, where=None, \*\*kwargs)

Return the fractional and integral parts of a tensor, element-wise.

The fractional and integral parts are negative if the given number is
negative.

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
  * **y1** (*Tensor*) – Fractional part of x.
  * **y2** (*Tensor*) – Integral part of x.

### Notes

For integer input the return values are floats.

#### SEE ALSO
[`divmod`](https://docs.python.org/3/library/functions.html#divmod)
: `divmod(x, 1)` is equivalent to `modf` with the return values switched, except it always has a positive remainder.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.modf([0, 3.5]).execute()
(array([ 0. ,  0.5]), array([ 0.,  3.]))
>>> mt.modf(-0.5).execute()
(-0.5, -0)
```
