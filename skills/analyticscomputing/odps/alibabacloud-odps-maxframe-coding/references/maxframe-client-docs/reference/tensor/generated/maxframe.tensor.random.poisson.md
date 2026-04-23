# maxframe.tensor.random.poisson

### maxframe.tensor.random.poisson(lam=1.0, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a Poisson distribution.

The Poisson distribution is the limit of the binomial distribution
for large N.

* **Parameters:**
  * **lam** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Expectation of interval, should be >= 0. A sequence of expectation
    intervals must be broadcastable over the requested size.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `lam` is a scalar. Otherwise,
    `mt.array(lam).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized Poisson distribution.
* **Return type:**
  Tensor or scalar

### Notes

The Poisson distribution

$$
f(k; \lambda)=\frac{\lambda^k e^{-\lambda}}{k!}

$$

For events with an expected separation $\lambda$ the Poisson
distribution $f(k; \lambda)$ describes the probability of
$k$ events occurring within the observed
interval $\lambda$.

Because the output is limited to the range of the C long type, a
ValueError is raised when lam is within 10 sigma of the maximum
representable value.

### References

* <a id='id1'>**[1]**</a> Weisstein, Eric W. “Poisson Distribution.” From MathWorld–A Wolfram Web Resource. [http://mathworld.wolfram.com/PoissonDistribution.html](http://mathworld.wolfram.com/PoissonDistribution.html)
* <a id='id2'>**[2]**</a> Wikipedia, “Poisson distribution”, [http://en.wikipedia.org/wiki/Poisson_distribution](http://en.wikipedia.org/wiki/Poisson_distribution)

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
>>> s = mt.random.poisson(5, 10000)
```

Display histogram of the sample:

```pycon
>>> import matplotlib.pyplot as plt
>>> count, bins, ignored = plt.hist(s.execute(), 14, normed=True)
>>> plt.show()
```

Draw each 100 values for lambda 100 and 500:

```pycon
>>> s = mt.random.poisson(lam=(100., 500.), size=(100, 2))
```
