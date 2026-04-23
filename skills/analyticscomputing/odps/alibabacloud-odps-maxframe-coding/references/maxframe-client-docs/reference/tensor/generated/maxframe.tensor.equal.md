# maxframe.tensor.equal

### maxframe.tensor.equal(x1, x2, out=None, where=None, \*\*kwargs)

Return (x1 == x2) element-wise.

* **Parameters:**
  * **x1** (*array_like*) – Input tensors of the same shape.
  * **x2** (*array_like*) – Input tensors of the same shape.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated array is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs** – For other keyword-only arguments, see the
    [ufunc docs](https://numpy.org/doc/stable/reference/ufuncs.html#ufuncs-kwargs).
* **Returns:**
  **out** – Output tensor of bools, or a single bool if x1 and x2 are scalars.
* **Return type:**
  Tensor or [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`not_equal`](maxframe.tensor.not_equal.md#maxframe.tensor.not_equal), [`greater_equal`](maxframe.tensor.greater_equal.md#maxframe.tensor.greater_equal), [`less_equal`](maxframe.tensor.less_equal.md#maxframe.tensor.less_equal), [`greater`](maxframe.tensor.greater.md#maxframe.tensor.greater), [`less`](maxframe.tensor.less.md#maxframe.tensor.less)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.equal([0, 1, 3], mt.arange(3)).execute()
array([ True,  True, False])
```

What is compared are values, not types. So an int (1) and a tensor of
length one can evaluate as True:

```pycon
>>> mt.equal(1, mt.ones(1))
array([ True])
```
