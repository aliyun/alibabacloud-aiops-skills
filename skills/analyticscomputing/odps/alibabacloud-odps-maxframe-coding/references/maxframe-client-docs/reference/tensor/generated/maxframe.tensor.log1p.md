# maxframe.tensor.log1p

### maxframe.tensor.log1p(x, out=None, where=None, \*\*kwargs)

Return the natural logarithm of one plus the input tensor, element-wise.

Calculates `log(1 + x)`.

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
  **y** – Natural logarithm of 1 + x, element-wise.
* **Return type:**
  Tensor

#### SEE ALSO
[`expm1`](maxframe.tensor.expm1.md#maxframe.tensor.expm1)
: `exp(x) - 1`, the inverse of log1p.

### Notes

For real-valued input, log1p is accurate also for x so small
that 1 + x == 1 in floating-point accuracy.

Logarithm is a multivalued function: for each x there is an infinite
number of z such that exp(z) = 1 + x. The convention is to return
the z whose imaginary part lies in [-pi, pi].

For real-valued input data types, log1p always returns real output.
For each value that cannot be expressed as a real number or infinity,
it yields `nan` and sets the invalid floating point error flag.

For complex-valued input, log1p is a complex analytical function that
has a branch cut [-inf, -1] and is continuous from above on it.
log1p handles the floating-point negative zero as an infinitesimal
negative number, conforming to the C99 standard.

### References

* <a id='id1'>**[1]**</a> M. Abramowitz and I.A. Stegun, “Handbook of Mathematical Functions”, 10th printing, 1964, pp. 67. [http://www.math.sfu.ca/~cbm/aands/](http://www.math.sfu.ca/~cbm/aands/)
* <a id='id2'>**[2]**</a> Wikipedia, “Logarithm”. [http://en.wikipedia.org/wiki/Logarithm](http://en.wikipedia.org/wiki/Logarithm)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.log1p(1e-99).execute()
1e-99
>>> mt.log(1 + 1e-99).execute()
0.0
```
