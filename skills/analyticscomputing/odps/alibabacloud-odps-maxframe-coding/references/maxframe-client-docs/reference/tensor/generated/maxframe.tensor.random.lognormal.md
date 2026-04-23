# maxframe.tensor.random.lognormal

### maxframe.tensor.random.lognormal(mean=0.0, sigma=1.0, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a log-normal distribution.

Draw samples from a log-normal distribution with specified mean,
standard deviation, and array shape.  Note that the mean and standard
deviation are not the values for the distribution itself, but of the
underlying normal distribution it is derived from.

* **Parameters:**
  * **mean** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats* *,* *optional*) – Mean value of the underlying normal distribution. Default is 0.
  * **sigma** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats* *,* *optional*) – Standard deviation of the underlying normal distribution. Should
    be greater than zero. Default is 1.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `mean` and `sigma` are both scalars.
    Otherwise, `np.broadcast(mean, sigma).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized log-normal distribution.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`scipy.stats.lognorm`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.lognorm.html#scipy.stats.lognorm)
: probability density function, distribution, cumulative density function, etc.

### Notes

A variable x has a log-normal distribution if log(x) is normally
distributed.  The probability density function for the log-normal
distribution is:

$$
p(x) = \frac{1}{\sigma x \sqrt{2\pi}}
e^{(-\frac{(ln(x)-\mu)^2}{2\sigma^2})}

$$

where $\mu$ is the mean and $\sigma$ is the standard
deviation of the normally distributed logarithm of the variable.
A log-normal distribution results if a random variable is the *product*
of a large number of independent, identically-distributed variables in
the same way that a normal distribution results if the variable is the
*sum* of a large number of independent, identically-distributed
variables.

### References

* <a id='id1'>**[1]**</a> Limpert, E., Stahel, W. A., and Abbt, M., “Log-normal Distributions across the Sciences: Keys and Clues,” BioScience, Vol. 51, No. 5, May, 2001. [http://stat.ethz.ch/~stahel/lognormal/bioscience.pdf](http://stat.ethz.ch/~stahel/lognormal/bioscience.pdf)
* <a id='id2'>**[2]**</a> Reiss, R.D. and Thomas, M., “Statistical Analysis of Extreme Values,” Basel: Birkhauser Verlag, 2001, pp. 31-32.

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mu, sigma = 3., 1. # mean and standard deviation
>>> s = mt.random.lognormal(mu, sigma, 1000)
```

Display the histogram of the samples, along with
the probability density function:

```pycon
>>> import matplotlib.pyplot as plt
>>> count, bins, ignored = plt.hist(s.execute(), 100, normed=True, align='mid')
```

```pycon
>>> x = mt.linspace(min(bins), max(bins), 10000)
>>> pdf = (mt.exp(-(mt.log(x) - mu)**2 / (2 * sigma**2))
...        / (x * sigma * mt.sqrt(2 * mt.pi)))
```

```pycon
>>> plt.plot(x.execute(), pdf.execute(), linewidth=2, color='r')
>>> plt.axis('tight')
>>> plt.show()
```

Demonstrate that taking the products of random samples from a uniform
distribution can be fit well by a log-normal probability density
function.

```pycon
>>> # Generate a thousand samples: each is the product of 100 random
>>> # values, drawn from a normal distribution.
>>> b = []
>>> for i in range(1000):
...    a = 10. + mt.random.random(100)
...    b.append(mt.product(a).execute())
```

```pycon
>>> b = mt.array(b) / mt.min(b) # scale values to be positive
>>> count, bins, ignored = plt.hist(b.execute(), 100, normed=True, align='mid')
>>> sigma = mt.std(mt.log(b))
>>> mu = mt.mean(mt.log(b))
```

```pycon
>>> x = mt.linspace(min(bins), max(bins), 10000)
>>> pdf = (mt.exp(-(mt.log(x) - mu)**2 / (2 * sigma**2))
...        / (x * sigma * mt.sqrt(2 * mt.pi)))
```

```pycon
>>> plt.plot(x.execute(), pdf.execute(), color='r', linewidth=2)
>>> plt.show()
```
