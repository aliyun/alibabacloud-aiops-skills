# maxframe.tensor.expm1

### maxframe.tensor.expm1(x, out=None, where=None, \*\*kwargs)

Calculate `exp(x) - 1` for all elements in the tensor.

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
  **out** – Element-wise exponential minus one: `out = exp(x) - 1`.
* **Return type:**
  Tensor

#### SEE ALSO
[`log1p`](maxframe.tensor.log1p.md#maxframe.tensor.log1p)
: `log(1 + x)`, the inverse of expm1.

### Notes

This function provides greater precision than `exp(x) - 1`
for small values of `x`.

### Examples

The true value of `exp(1e-10) - 1` is `1.00000000005e-10` to
about 32 significant digits. This example shows the superiority of
expm1 in this case.

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.expm1(1e-10).execute()
1.00000000005e-10
>>> (mt.exp(1e-10) - 1).execute()
1.000000082740371e-10
```
