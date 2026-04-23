# maxframe.tensor.log2

### maxframe.tensor.log2(x, out=None, where=None, \*\*kwargs)

Base-2 logarithm of x.

* **Parameters:**
  * **x** (*array_like*) – Input values.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – Base-2 logarithm of x.
* **Return type:**
  Tensor

#### SEE ALSO
[`log`](maxframe.tensor.log.md#maxframe.tensor.log), [`log10`](maxframe.tensor.log10.md#maxframe.tensor.log10), [`log1p`](maxframe.tensor.log1p.md#maxframe.tensor.log1p), `Logarithm`, `number`, `whose`, `pi`, `For`, [`None`](https://docs.python.org/3/library/constants.html#None), `For`, `it`, `For`, [`None`](https://docs.python.org/3/library/constants.html#None), `has`, `0`, `handles`, `number`, `conforming`

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([0, 1, 2, 2**4])
>>> mt.log2(x).execute()
array([-Inf,   0.,   1.,   4.])
```

```pycon
>>> xi = mt.array([0+1.j, 1, 2+0.j, 4.j])
>>> mt.log2(xi).execute()
array([ 0.+2.26618007j,  0.+0.j        ,  1.+0.j        ,  2.+2.26618007j])
```
