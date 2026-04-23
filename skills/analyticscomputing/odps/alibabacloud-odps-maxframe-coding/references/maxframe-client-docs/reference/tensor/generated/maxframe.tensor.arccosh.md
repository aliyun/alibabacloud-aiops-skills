# maxframe.tensor.arccosh

### maxframe.tensor.arccosh(x, out=None, where=None, \*\*kwargs)

Inverse hyperbolic cosine, element-wise.

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
  **arccosh** – Array of the same shape as x.
* **Return type:**
  Tensor

#### SEE ALSO
[`cosh`](maxframe.tensor.cosh.md#maxframe.tensor.cosh), [`arcsinh`](maxframe.tensor.arcsinh.md#maxframe.tensor.arcsinh), [`sinh`](maxframe.tensor.sinh.md#maxframe.tensor.sinh), [`arctanh`](maxframe.tensor.arctanh.md#maxframe.tensor.arctanh), [`tanh`](maxframe.tensor.tanh.md#maxframe.tensor.tanh)

### Notes

arccosh is a multivalued function: for each x there are infinitely
many numbers z such that cosh(z) = x. The convention is to return the
z whose imaginary part lies in [-pi, pi] and the real part in
`[0, inf]`.

For real-valued input data types, arccosh always returns real output.
For each value that cannot be expressed as a real number or infinity, it
yields `nan` and sets the invalid floating point error flag.

For complex-valued input, arccosh is a complex analytical function that
has a branch cut [-inf, 1] and is continuous from above on it.

### References

* <a id='id1'>**[1]**</a> M. Abramowitz and I.A. Stegun, “Handbook of Mathematical Functions”, 10th printing, 1964, pp. 86. [http://www.math.sfu.ca/~cbm/aands/](http://www.math.sfu.ca/~cbm/aands/)
* <a id='id2'>**[2]**</a> Wikipedia, “Inverse hyperbolic function”, [http://en.wikipedia.org/wiki/Arccosh](http://en.wikipedia.org/wiki/Arccosh)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.arccosh([mt.e, 10.0]).execute()
array([ 1.65745445,  2.99322285])
>>> mt.arccosh(1).execute()
0.0
```
