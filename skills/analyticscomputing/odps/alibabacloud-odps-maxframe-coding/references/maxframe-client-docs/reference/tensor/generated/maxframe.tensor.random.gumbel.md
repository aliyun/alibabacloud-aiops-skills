# maxframe.tensor.random.gumbel

### maxframe.tensor.random.gumbel(loc=0.0, scale=1.0, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a Gumbel distribution.

Draw samples from a Gumbel distribution with specified location and
scale.  For more information on the Gumbel distribution, see
Notes and References below.

* **Parameters:**
  * **loc** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats* *,* *optional*) – The location of the mode of the distribution. Default is 0.
  * **scale** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats* *,* *optional*) – The scale parameter of the distribution. Default is 1.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `loc` and `scale` are both scalars.
    Otherwise, `np.broadcast(loc, scale).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized Gumbel distribution.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`scipy.stats.gumbel_l`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gumbel_l.html#scipy.stats.gumbel_l), [`scipy.stats.gumbel_r`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gumbel_r.html#scipy.stats.gumbel_r), [`scipy.stats.genextreme`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.genextreme.html#scipy.stats.genextreme), [`weibull`](maxframe.tensor.random.weibull.md#maxframe.tensor.random.weibull)

### Notes

The Gumbel (or Smallest Extreme Value (SEV) or the Smallest Extreme
Value Type I) distribution is one of a class of Generalized Extreme
Value (GEV) distributions used in modeling extreme value problems.
The Gumbel is a special case of the Extreme Value Type I distribution
for maximums from distributions with “exponential-like” tails.

The probability density for the Gumbel distribution is

$$
p(x) = \frac{e^{-(x - \mu)/ \beta}}{\beta} e^{ -e^{-(x - \mu)/
\beta}},

$$

where $\mu$ is the mode, a location parameter, and
$\beta$ is the scale parameter.

The Gumbel (named for German mathematician Emil Julius Gumbel) was used
very early in the hydrology literature, for modeling the occurrence of
flood events. It is also used for modeling maximum wind speed and
rainfall rates.  It is a “fat-tailed” distribution - the probability of
an event in the tail of the distribution is larger than if one used a
Gaussian, hence the surprisingly frequent occurrence of 100-year
floods. Floods were initially modeled as a Gaussian process, which
underestimated the frequency of extreme events.

It is one of a class of extreme value distributions, the Generalized
Extreme Value (GEV) distributions, which also includes the Weibull and
Frechet.

The function has a mean of $\mu + 0.57721\beta$ and a variance
of $\frac{\pi^2}{6}\beta^2$.

### References

* <a id='id1'>**[1]**</a> Gumbel, E. J., “Statistics of Extremes,” New York: Columbia University Press, 1958.
* <a id='id2'>**[2]**</a> Reiss, R.-D. and Thomas, M., “Statistical Analysis of Extreme Values from Insurance, Finance, Hydrology and Other Fields,” Basel: Birkhauser Verlag, 2001.

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mu, beta = 0, 0.1 # location and scale
>>> s = mt.random.gumbel(mu, beta, 1000).execute()
```

Display the histogram of the samples, along with
the probability density function:

```pycon
>>> import matplotlib.pyplot as plt
>>> import numpy as np
>>> count, bins, ignored = plt.hist(s, 30, normed=True)
>>> plt.plot(bins, (1/beta)*np.exp(-(bins - mu)/beta)
...          * np.exp( -np.exp( -(bins - mu) /beta) ),
...          linewidth=2, color='r')
>>> plt.show()
```

Show how an extreme value distribution can arise from a Gaussian process
and compare to a Gaussian:

```pycon
>>> means = []
>>> maxima = []
>>> for i in range(0,1000) :
...    a = mt.random.normal(mu, beta, 1000)
...    means.append(a.mean().execute())
...    maxima.append(a.max().execute())
>>> count, bins, ignored = plt.hist(maxima, 30, normed=True)
>>> beta = mt.std(maxima) * mt.sqrt(6) / mt.pi
>>> mu = mt.mean(maxima) - 0.57721*beta
>>> plt.plot(bins, ((1/beta)*mt.exp(-(bins - mu)/beta)
...          * mt.exp(-mt.exp(-(bins - mu)/beta))).execute(),
...          linewidth=2, color='r')
>>> plt.plot(bins, (1/(beta * mt.sqrt(2 * mt.pi))
...          * mt.exp(-(bins - mu)**2 / (2 * beta**2))).execute(),
...          linewidth=2, color='g')
>>> plt.show()
```
