# maxframe.tensor.square

### maxframe.tensor.square(x, out=None, where=None, \*\*kwargs)

Return the element-wise square of the input.

* **Parameters:**
  * **x** (*array_like*) – Input data.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated array is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **out** – Element-wise x\*x, of the same shape and dtype as x.
  Returns scalar if x is a scalar.
* **Return type:**
  Tensor

#### SEE ALSO
[`sqrt`](maxframe.tensor.sqrt.md#maxframe.tensor.sqrt), [`power`](maxframe.tensor.power.md#maxframe.tensor.power)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.square([-1j, 1]).execute()
array([-1.-0.j,  1.+0.j])
```
