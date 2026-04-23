# maxframe.tensor.special.erf

### maxframe.tensor.special.erf(x, out=None, where=None, \*\*kwargs)

Returns the error function of complex argument.

It is defined as `2/sqrt(pi)*integral(exp(-t**2), t=0..z)`.

* **Parameters:**
  **x** (*Tensor*) – Input tensor.
* **Returns:**
  **res** – The values of the error function at the given points x.
* **Return type:**
  Tensor

#### SEE ALSO
[`erfc`](maxframe.tensor.special.erfc.md#maxframe.tensor.special.erfc), [`erfinv`](maxframe.tensor.special.erfinv.md#maxframe.tensor.special.erfinv), [`erfcinv`](maxframe.tensor.special.erfcinv.md#maxframe.tensor.special.erfcinv), [`wofz`](maxframe.tensor.special.wofz.md#maxframe.tensor.special.wofz), [`erfcx`](maxframe.tensor.special.erfcx.md#maxframe.tensor.special.erfcx), [`erfi`](maxframe.tensor.special.erfi.md#maxframe.tensor.special.erfi)

### Notes

The cumulative of the unit normal distribution is given by
`Phi(z) = 1/2[1 + erf(z/sqrt(2))]`.

### References

* <a id='id1'>**[1]**</a> [https://en.wikipedia.org/wiki/Error_function](https://en.wikipedia.org/wiki/Error_function)
* <a id='id2'>**[2]**</a> Milton Abramowitz and Irene A. Stegun, eds. Handbook of Mathematical Functions with Formulas, Graphs, and Mathematical Tables. New York: Dover, 1972. [http://www.math.sfu.ca/~cbm/aands/page_297.htm](http://www.math.sfu.ca/~cbm/aands/page_297.htm)
* <a id='id3'>**[3]**</a> Steven G. Johnson, Faddeeva W function implementation. [http://ab-initio.mit.edu/Faddeeva](http://ab-initio.mit.edu/Faddeeva)

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> from maxframe.tensor import special
>>> import matplotlib.pyplot as plt
>>> x = mt.linspace(-3, 3)
>>> plt.plot(x, special.erf(x))
>>> plt.xlabel('$x$')
>>> plt.ylabel('$erf(x)$')
>>> plt.show()
```
