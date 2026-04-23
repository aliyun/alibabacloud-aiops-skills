# maxframe.tensor.less_equal

### maxframe.tensor.less_equal(x1, x2, out=None, where=None, \*\*kwargs)

Return the truth value of (x1 =< x2) element-wise.

* **Parameters:**
  * **x1** (*array_like*) – Input tensors.  If `x1.shape != x2.shape`, they must be
    broadcastable to a common shape (which may be the shape of one or
    the other).
  * **x2** (*array_like*) – Input tensors.  If `x1.shape != x2.shape`, they must be
    broadcastable to a common shape (which may be the shape of one or
    the other).
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **out** – Array of bools, or a single bool if x1 and x2 are scalars.
* **Return type:**
  [bool](https://docs.python.org/3/library/functions.html#bool) or tensor of [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`greater`](maxframe.tensor.greater.md#maxframe.tensor.greater), [`less`](maxframe.tensor.less.md#maxframe.tensor.less), [`greater_equal`](maxframe.tensor.greater_equal.md#maxframe.tensor.greater_equal), [`equal`](maxframe.tensor.equal.md#maxframe.tensor.equal), [`not_equal`](maxframe.tensor.not_equal.md#maxframe.tensor.not_equal)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.less_equal([4, 2, 1], [2, 2, 2]).execute()
array([False,  True,  True])
```
