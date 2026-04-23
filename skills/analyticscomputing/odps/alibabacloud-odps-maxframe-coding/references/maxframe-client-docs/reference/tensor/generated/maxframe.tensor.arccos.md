# maxframe.tensor.arccos

### maxframe.tensor.arccos(x, out=None, where=None, \*\*kwargs)

Trigonometric inverse cosine, element-wise.

The inverse of cos so that, if `y = cos(x)`, then `x = arccos(y)`.

* **Parameters:**
  * **x** (*array_like*) – x-coordinate on the unit circle.
    For real arguments, the domain is [-1, 1].
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **angle** – The angle of the ray intersecting the unit circle at the given
  x-coordinate in radians [0, pi]. If x is a scalar then a
  scalar is returned, otherwise an array of the same shape as x
  is returned.
* **Return type:**
  Tensor

#### SEE ALSO
[`cos`](maxframe.tensor.cos.md#maxframe.tensor.cos), [`arctan`](maxframe.tensor.arctan.md#maxframe.tensor.arctan), [`arcsin`](maxframe.tensor.arcsin.md#maxframe.tensor.arcsin)

### Notes

arccos is a multivalued function: for each x there are infinitely
many numbers z such that cos(z) = x. The convention is to return
the angle z whose real part lies in [0, pi].

For real-valued input data types, arccos always returns real output.
For each value that cannot be expressed as a real number or infinity,
it yields `nan` and sets the invalid floating point error flag.

For complex-valued input, arccos is a complex analytic function that
has branch cuts [-inf, -1] and [1, inf] and is continuous from
above on the former and from below on the latter.

The inverse cos is also known as acos or cos^-1.

### References

M. Abramowitz and I.A. Stegun, “Handbook of Mathematical Functions”,
10th printing, 1964, pp. 79. [http://www.math.sfu.ca/~cbm/aands/](http://www.math.sfu.ca/~cbm/aands/)

### Examples

We expect the arccos of 1 to be 0, and of -1 to be pi:
>>> import maxframe.tensor as mt

```pycon
>>> mt.arccos([1, -1]).execute()
array([ 0.        ,  3.14159265])
```

Plot arccos:

```pycon
>>> import matplotlib.pyplot as plt
>>> x = mt.linspace(-1, 1, num=100)
>>> plt.plot(x.execute(), mt.arccos(x).execute())
>>> plt.axis('tight')
>>> plt.show()
```
