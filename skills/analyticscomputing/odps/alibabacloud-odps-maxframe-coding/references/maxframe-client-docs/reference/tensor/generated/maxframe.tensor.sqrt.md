# maxframe.tensor.sqrt

### maxframe.tensor.sqrt(x, out=None, where=None, \*\*kwargs)

Return the positive square-root of an tensor, element-wise.

* **Parameters:**
  * **x** (*array_like*) – The values whose square-roots are required.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – An tensor of the same shape as x, containing the positive
  square-root of each element in x.  If any element in x is
  complex, a complex tensor is returned (and the square-roots of
  negative reals are calculated).  If all of the elements in x
  are real, so is y, with negative elements returning `nan`.
  If out was provided, y is a reference to it.
* **Return type:**
  Tensor

### Notes

*sqrt* has–consistent with common convention–as its branch cut the
real “interval” [-inf, 0), and is continuous from above on it.
A branch cut is a curve in the complex plane across which a given
complex function fails to be continuous.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.sqrt([1,4,9]).execute()
array([ 1.,  2.,  3.])
```

```pycon
>>> mt.sqrt([4, -1, -3+4J]).execute()
array([ 2.+0.j,  0.+1.j,  1.+2.j])
```

```pycon
>>> mt.sqrt([4, -1, mt.inf]).execute()
array([  2.,  NaN,  Inf])
```
