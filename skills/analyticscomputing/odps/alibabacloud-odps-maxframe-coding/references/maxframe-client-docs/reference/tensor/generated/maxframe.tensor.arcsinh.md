# maxframe.tensor.arcsinh

### maxframe.tensor.arcsinh(x, out=None, where=None, \*\*kwargs)

Inverse hyperbolic sine element-wise.

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
  **out** – Tensor of of the same shape as x.
* **Return type:**
  Tensor

### Notes

arcsinh is a multivalued function: for each x there are infinitely
many numbers z such that sinh(z) = x. The convention is to return the
z whose imaginary part lies in [-pi/2, pi/2].

For real-valued input data types, arcsinh always returns real output.
For each value that cannot be expressed as a real number or infinity, it
returns `nan` and sets the invalid floating point error flag.

For complex-valued input, arccos is a complex analytical function that
has branch cuts [1j, infj] and [-1j, -infj] and is continuous from
the right on the former and from the left on the latter.

The inverse hyperbolic sine is also known as asinh or `sinh^-1`.

### References

* <a id='id1'>**[1]**</a> M. Abramowitz and I.A. Stegun, “Handbook of Mathematical Functions”, 10th printing, 1964, pp. 86. [http://www.math.sfu.ca/~cbm/aands/](http://www.math.sfu.ca/~cbm/aands/)
* <a id='id2'>**[2]**</a> Wikipedia, “Inverse hyperbolic function”, [http://en.wikipedia.org/wiki/Arcsinh](http://en.wikipedia.org/wiki/Arcsinh)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.arcsinh(mt.array([mt.e, 10.0])).execute()
array([ 1.72538256,  2.99822295])
```
