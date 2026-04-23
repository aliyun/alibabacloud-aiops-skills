# maxframe.tensor.not_equal

### maxframe.tensor.not_equal(x1, x2, out=None, where=None, \*\*kwargs)

Return (x1 != x2) element-wise.

* **Parameters:**
  * **x1** (*array_like*) – Input tensors.
  * **x2** (*array_like*) – Input tensors.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **not_equal** – For each element in x1, x2, return True if x1 is not equal
  to x2 and False otherwise.
* **Return type:**
  tensor bool, scalar bool

#### SEE ALSO
[`equal`](maxframe.tensor.equal.md#maxframe.tensor.equal), [`greater`](maxframe.tensor.greater.md#maxframe.tensor.greater), [`greater_equal`](maxframe.tensor.greater_equal.md#maxframe.tensor.greater_equal), [`less`](maxframe.tensor.less.md#maxframe.tensor.less), [`less_equal`](maxframe.tensor.less_equal.md#maxframe.tensor.less_equal)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.not_equal([1.,2.], [1., 3.]).execute()
array([False,  True])
>>> mt.not_equal([1, 2], [[1, 3],[1, 4]]).execute()
array([[False,  True],
       [False,  True]])
```
