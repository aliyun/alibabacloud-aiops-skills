# maxframe.tensor.log

### maxframe.tensor.log(x, out=None, where=None, \*\*kwargs)

Natural logarithm, element-wise.

The natural logarithm log is the inverse of the exponential function,
so that log(exp(x)) = x. The natural logarithm is logarithm in base
e.

* **Parameters:**
  * **x** (*array_like*) – Input value.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The natural logarithm of x, element-wise.
* **Return type:**
  Tensor

#### SEE ALSO
[`log10`](maxframe.tensor.log10.md#maxframe.tensor.log10), [`log2`](maxframe.tensor.log2.md#maxframe.tensor.log2), [`log1p`](maxframe.tensor.log1p.md#maxframe.tensor.log1p)

### Notes

Logarithm is a multivalued function: for each x there is an infinite
number of z such that exp(z) = x. The convention is to return the
z whose imaginary part lies in [-pi, pi].

For real-valued input data types, log always returns real output. For
each value that cannot be expressed as a real number or infinity, it
yields `nan` and sets the invalid floating point error flag.

For complex-valued input, log is a complex analytical function that
has a branch cut [-inf, 0] and is continuous from above on it. log
handles the floating-point negative zero as an infinitesimal negative
number, conforming to the C99 standard.

### References

* <a id='id1'>**[1]**</a> M. Abramowitz and I.A. Stegun, “Handbook of Mathematical Functions”, 10th printing, 1964, pp. 67. [http://www.math.sfu.ca/~cbm/aands/](http://www.math.sfu.ca/~cbm/aands/)
* <a id='id2'>**[2]**</a> Wikipedia, “Logarithm”. [http://en.wikipedia.org/wiki/Logarithm](http://en.wikipedia.org/wiki/Logarithm)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.log([1, mt.e, mt.e**2, 0]).execute()
array([  0.,   1.,   2., -Inf])
```
