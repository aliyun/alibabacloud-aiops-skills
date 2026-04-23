# maxframe.tensor.random.pareto

### maxframe.tensor.random.pareto(a, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a Pareto II or Lomax distribution with
specified shape.

The Lomax or Pareto II distribution is a shifted Pareto
distribution. The classical Pareto distribution can be
obtained from the Lomax distribution by adding 1 and
multiplying by the scale parameter `m` (see Notes).  The
smallest value of the Lomax distribution is zero while for the
classical Pareto distribution it is `mu`, where the standard
Pareto distribution has location `mu = 1`.  Lomax can also
be considered as a simplified version of the Generalized
Pareto distribution (available in SciPy), with the scale set
to one and the location set to zero.

The Pareto distribution must be greater than zero, and is
unbounded above.  It is also known as the “80-20 rule”.  In
this distribution, 80 percent of the weights are in the lowest
20 percent of the range, while the other 20 percent fill the
remaining 80 percent of the range.

* **Parameters:**
  * **a** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Shape of the distribution. Should be greater than zero.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `a` is a scalar.  Otherwise,
    `mt.array(a).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized Pareto distribution.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`scipy.stats.lomax`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.lomax.html#scipy.stats.lomax)
: probability density function, distribution or cumulative density function, etc.

[`scipy.stats.genpareto`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.genpareto.html#scipy.stats.genpareto)
: probability density function, distribution or cumulative density function, etc.

### Notes

The probability density for the Pareto distribution is

$$
p(x) = \frac{am^a}{x^{a+1}}

$$

where $a$ is the shape and $m$ the scale.

The Pareto distribution, named after the Italian economist
Vilfredo Pareto, is a power law probability distribution
useful in many real world problems.  Outside the field of
economics it is generally referred to as the Bradford
distribution. Pareto developed the distribution to describe
the distribution of wealth in an economy.  It has also found
use in insurance, web page access statistics, oil field sizes,
and many other problems, including the download frequency for
projects in Sourceforge <sup>[1](#id2)</sup>.  It is one of the so-called
“fat-tailed” distributions.

### References

* <a id='id2'>**[1]**</a> Francis Hunt and Paul Johnson, On the Pareto Distribution of Sourceforge projects.
* <a id='id3'>**[2]**</a> Pareto, V. (1896). Course of Political Economy. Lausanne.
* <a id='id4'>**[3]**</a> Reiss, R.D., Thomas, M.(2001), Statistical Analysis of Extreme Values, Birkhauser Verlag, Basel, pp 23-30.
* <a id='id5'>**[4]**</a> Wikipedia, “Pareto distribution”, [http://en.wikipedia.org/wiki/Pareto_distribution](http://en.wikipedia.org/wiki/Pareto_distribution)

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a, m = 3., 2.  # shape and mode
>>> s = (mt.random.pareto(a, 1000) + 1) * m
```

Display the histogram of the samples, along with the probability
density function:

```pycon
>>> import matplotlib.pyplot as plt
>>> count, bins, _ = plt.hist(s.execute(), 100, normed=True)
>>> fit = a*m**a / bins**(a+1)
>>> plt.plot(bins, max(count)*fit/max(fit), linewidth=2, color='r')
>>> plt.show()
```
