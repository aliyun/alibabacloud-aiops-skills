# maxframe.tensor.floor

### maxframe.tensor.floor(x, out=None, where=None, \*\*kwargs)

Return the floor of the input, element-wise.

The floor of the scalar x is the largest integer i, such that
i <= x.  It is often denoted as $\lfloor x \rfloor$.

* **Parameters:**
  * **x** (*array_like*) – Input data.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The floor of each element in x.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`ceil`](maxframe.tensor.ceil.md#maxframe.tensor.ceil), [`trunc`](maxframe.tensor.trunc.md#maxframe.tensor.trunc), [`rint`](maxframe.tensor.rint.md#maxframe.tensor.rint)

### Notes

Some spreadsheet programs calculate the “floor-towards-zero”, in other
words `floor(-2.5) == -2`.  NumPy instead uses the definition of
floor where floor(-2.5) == -3.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([-1.7, -1.5, -0.2, 0.2, 1.5, 1.7, 2.0])
>>> mt.floor(a).execute()
array([-2., -2., -1.,  0.,  1.,  1.,  2.])
```
