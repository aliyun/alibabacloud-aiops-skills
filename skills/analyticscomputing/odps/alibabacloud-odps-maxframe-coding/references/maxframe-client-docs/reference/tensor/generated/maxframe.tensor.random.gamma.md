# maxframe.tensor.random.gamma

### maxframe.tensor.random.gamma(shape, scale=1.0, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a Gamma distribution.

Samples are drawn from a Gamma distribution with specified parameters,
shape (sometimes designated “k”) and scale (sometimes designated
“theta”), where both parameters are > 0.

* **Parameters:**
  * **shape** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – The shape of the gamma distribution. Should be greater than zero.
  * **scale** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats* *,* *optional*) – The scale of the gamma distribution. Should be greater than zero.
    Default is equal to 1.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `shape` and `scale` are both scalars.
    Otherwise, `np.broadcast(shape, scale).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized gamma distribution.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`scipy.stats.gamma`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gamma.html#scipy.stats.gamma)
: probability density function, distribution or cumulative density function, etc.

### Notes

The probability density for the Gamma distribution is

$$
p(x) = x^{k-1}\frac{e^{-x/\theta}}{\theta^k\Gamma(k)},

$$

where $k$ is the shape and $\theta$ the scale,
and $\Gamma$ is the Gamma function.

The Gamma distribution is often used to model the times to failure of
electronic components, and arises naturally in processes for which the
waiting times between Poisson distributed events are relevant.

### References

* <a id='id1'>**[1]**</a> Weisstein, Eric W. “Gamma Distribution.” From MathWorld–A Wolfram Web Resource. [http://mathworld.wolfram.com/GammaDistribution.html](http://mathworld.wolfram.com/GammaDistribution.html)
* <a id='id2'>**[2]**</a> Wikipedia, “Gamma distribution”, [http://en.wikipedia.org/wiki/Gamma_distribution](http://en.wikipedia.org/wiki/Gamma_distribution)

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> shape, scale = 2., 2.  # mean=4, std=2*sqrt(2)
>>> s = mt.random.gamma(shape, scale, 1000).execute()
```

Display the histogram of the samples, along with
the probability density function:

```pycon
>>> import matplotlib.pyplot as plt
>>> import scipy.special as sps
>>> import numpy as np
>>> count, bins, ignored = plt.hist(s, 50, normed=True)
>>> y = bins**(shape-1)*(np.exp(-bins/scale) /
...                      (sps.gamma(shape)*scale**shape))
>>> plt.plot(bins, y, linewidth=2, color='r')
>>> plt.show()
```
