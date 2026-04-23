# maxframe.tensor.random.laplace

### maxframe.tensor.random.laplace(loc=0.0, scale=1.0, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from the Laplace or double exponential distribution with
specified location (or mean) and scale (decay).

The Laplace distribution is similar to the Gaussian/normal distribution,
but is sharper at the peak and has fatter tails. It represents the
difference between two independent, identically distributed exponential
random variables.

* **Parameters:**
  * **loc** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats* *,* *optional*) – The position, $\mu$, of the distribution peak. Default is 0.
  * **scale** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats* *,* *optional*) – $\lambda$, the exponential decay. Default is 1.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `loc` and `scale` are both scalars.
    Otherwise, `np.broadcast(loc, scale).size` samples are drawn.
  * **chunks** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized Laplace distribution.
* **Return type:**
  Tensor or scalar

### Notes

It has the probability density function

$$
f(x; \mu, \lambda) = \frac{1}{2\lambda}
\exp\left(-\frac{|x - \mu|}{\lambda}\right).

$$

The first law of Laplace, from 1774, states that the frequency
of an error can be expressed as an exponential function of the
absolute magnitude of the error, which leads to the Laplace
distribution. For many problems in economics and health
sciences, this distribution seems to model the data better
than the standard Gaussian distribution.

### References

* <a id='id1'>**[1]**</a> Abramowitz, M. and Stegun, I. A. (Eds.). “Handbook of Mathematical Functions with Formulas, Graphs, and Mathematical Tables, 9th printing,” New York: Dover, 1972.
* <a id='id2'>**[2]**</a> Kotz, Samuel, et. al. “The Laplace Distribution and Generalizations, “ Birkhauser, 2001.
* <a id='id3'>**[3]**</a> Weisstein, Eric W. “Laplace Distribution.” From MathWorld–A Wolfram Web Resource. [http://mathworld.wolfram.com/LaplaceDistribution.html](http://mathworld.wolfram.com/LaplaceDistribution.html)
* <a id='id4'>**[4]**</a> Wikipedia, “Laplace distribution”, [http://en.wikipedia.org/wiki/Laplace_distribution](http://en.wikipedia.org/wiki/Laplace_distribution)

### Examples

Draw samples from the distribution

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> loc, scale = 0., 1.
>>> s = mt.random.laplace(loc, scale, 1000)
```

Display the histogram of the samples, along with
the probability density function:

```pycon
>>> import matplotlib.pyplot as plt
>>> count, bins, ignored = plt.hist(s.execute(), 30, normed=True)
>>> x = mt.arange(-8., 8., .01)
>>> pdf = mt.exp(-abs(x-loc)/scale)/(2.*scale)
>>> plt.plot(x.execute(), pdf.execute())
```

Plot Gaussian for comparison:

```pycon
>>> g = (1/(scale * mt.sqrt(2 * np.pi)) *
...      mt.exp(-(x - loc)**2 / (2 * scale**2)))
>>> plt.plot(x.execute(),g.execute())
```
