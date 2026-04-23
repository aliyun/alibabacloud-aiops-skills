# maxframe.tensor.random.normal

### maxframe.tensor.random.normal(loc=0.0, scale=1.0, size=None, chunk_size=None, gpu=None, dtype=None)

Draw random samples from a normal (Gaussian) distribution.

The probability density function of the normal distribution, first
derived by De Moivre and 200 years later by both Gauss and Laplace
independently <sup>[2](#id5)</sup>, is often called the bell curve because of
its characteristic shape (see the example below).

The normal distributions occurs often in nature.  For example, it
describes the commonly occurring distribution of samples influenced
by a large number of tiny, random disturbances, each with its own
unique distribution <sup>[2](#id5)</sup>.

* **Parameters:**
  * **loc** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Mean (“centre”) of the distribution.
  * **scale** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Standard deviation (spread or “width”) of the distribution.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `loc` and `scale` are both scalars.
    Otherwise, `mt.broadcast(loc, scale).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized normal distribution.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`scipy.stats.norm`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.norm.html#scipy.stats.norm)
: probability density function, distribution or cumulative density function, etc.

### Notes

The probability density for the Gaussian distribution is

$$
p(x) = \frac{1}{\sqrt{ 2 \pi \sigma^2 }}
e^{ - \frac{ (x - \mu)^2 } {2 \sigma^2} },

$$

where $\mu$ is the mean and $\sigma$ the standard
deviation. The square of the standard deviation, $\sigma^2$,
is called the variance.

The function has its peak at the mean, and its “spread” increases with
the standard deviation (the function reaches 0.607 times its maximum at
$x + \sigma$ and $x - \sigma$ <sup>[2](#id5)</sup>).  This implies that
numpy.random.normal is more likely to return samples lying close to
the mean, rather than those far away.

### References

* <a id='id4'>**[1]**</a> Wikipedia, “Normal distribution”, [http://en.wikipedia.org/wiki/Normal_distribution](http://en.wikipedia.org/wiki/Normal_distribution)
* <a id='id5'>**[2]**</a> P. R. Peebles Jr., “Central Limit Theorem” in “Probability, Random Variables and Random Signal Principles”, 4th ed., 2001, pp. 51, 51, 125.

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mu, sigma = 0, 0.1 # mean and standard deviation
>>> s = mt.random.normal(mu, sigma, 1000)
```

Verify the mean and the variance:

```pycon
>>> (abs(mu - mt.mean(s)) < 0.01).execute()
True
```

```pycon
>>> (abs(sigma - mt.std(s, ddof=1)) < 0.01).execute()
True
```

Display the histogram of the samples, along with
the probability density function:

```pycon
>>> import matplotlib.pyplot as plt
>>> count, bins, ignored = plt.hist(s.execute(), 30, normed=True)
>>> plt.plot(bins, (1/(sigma * mt.sqrt(2 * mt.pi)) *
...                mt.exp( - (bins - mu)**2 / (2 * sigma**2) )).execute(),
...          linewidth=2, color='r')
>>> plt.show()
```
