# maxframe.tensor.random.standard_cauchy

### maxframe.tensor.random.standard_cauchy(size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a standard Cauchy distribution with mode = 0.

Also known as the Lorentz distribution.

* **Parameters:**
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  Default is None, in which case a
    single value is returned.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **samples** – The drawn samples.
* **Return type:**
  Tensor or scalar

### Notes

The probability density function for the full Cauchy distribution is

$$
P(x; x_0, \gamma) = \frac{1}{\pi \gamma \bigl[ 1+
(\frac{x-x_0}{\gamma})^2 \bigr] }

$$

and the Standard Cauchy distribution just sets $x_0=0$ and
$\gamma=1$

The Cauchy distribution arises in the solution to the driven harmonic
oscillator problem, and also describes spectral line broadening. It
also describes the distribution of values at which a line tilted at
a random angle will cut the x axis.

When studying hypothesis tests that assume normality, seeing how the
tests perform on data from a Cauchy distribution is a good indicator of
their sensitivity to a heavy-tailed distribution, since the Cauchy looks
very much like a Gaussian distribution, but with heavier tails.

### References

* <a id='id1'>**[1]**</a> NIST/SEMATECH e-Handbook of Statistical Methods, “Cauchy Distribution”, [http://www.itl.nist.gov/div898/handbook/eda/section3/eda3663.htm](http://www.itl.nist.gov/div898/handbook/eda/section3/eda3663.htm)
* <a id='id2'>**[2]**</a> Weisstein, Eric W. “Cauchy Distribution.” From MathWorld–A Wolfram Web Resource. [http://mathworld.wolfram.com/CauchyDistribution.html](http://mathworld.wolfram.com/CauchyDistribution.html)
* <a id='id3'>**[3]**</a> Wikipedia, “Cauchy distribution” [http://en.wikipedia.org/wiki/Cauchy_distribution](http://en.wikipedia.org/wiki/Cauchy_distribution)

### Examples

Draw samples and plot the distribution:

```pycon
>>> import maxframe.tensor as mt
>>> import matplotlib.pyplot as plt
```

```pycon
>>> s = mt.random.standard_cauchy(1000000)
>>> s = s[(s>-25) & (s<25)]  # truncate distribution so it plots well
>>> plt.hist(s.execute(), bins=100)
>>> plt.show()
```
