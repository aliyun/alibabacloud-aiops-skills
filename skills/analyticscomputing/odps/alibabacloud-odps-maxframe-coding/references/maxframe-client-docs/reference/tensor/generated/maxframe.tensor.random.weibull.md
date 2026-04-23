# maxframe.tensor.random.weibull

### maxframe.tensor.random.weibull(a, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a Weibull distribution.

Draw samples from a 1-parameter Weibull distribution with the given
shape parameter a.

$$
X = (-ln(U))^{1/a}

$$

Here, U is drawn from the uniform distribution over (0,1].

The more common 2-parameter Weibull, including a scale parameter
$\lambda$ is just $X = \lambda(-ln(U))^{1/a}$.

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
  **out** – Drawn samples from the parameterized Weibull distribution.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`scipy.stats.weibull_max`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.weibull_max.html#scipy.stats.weibull_max), [`scipy.stats.weibull_min`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.weibull_min.html#scipy.stats.weibull_min), [`scipy.stats.genextreme`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.genextreme.html#scipy.stats.genextreme), [`gumbel`](maxframe.tensor.random.gumbel.md#maxframe.tensor.random.gumbel)

### Notes

The Weibull (or Type III asymptotic extreme value distribution
for smallest values, SEV Type III, or Rosin-Rammler
distribution) is one of a class of Generalized Extreme Value
(GEV) distributions used in modeling extreme value problems.
This class includes the Gumbel and Frechet distributions.

The probability density for the Weibull distribution is

$$
p(x) = \frac{a}
{\lambda}(\frac{x}{\lambda})^{a-1}e^{-(x/\lambda)^a},

$$

where $a$ is the shape and $\lambda$ the scale.

The function has its peak (the mode) at
$\lambda(\frac{a-1}{a})^{1/a}$.

When `a = 1`, the Weibull distribution reduces to the exponential
distribution.

### References

* <a id='id1'>**[1]**</a> Waloddi Weibull, Royal Technical University, Stockholm, 1939 “A Statistical Theory Of The Strength Of Materials”, Ingeniorsvetenskapsakademiens Handlingar Nr 151, 1939, Generalstabens Litografiska Anstalts Forlag, Stockholm.
* <a id='id2'>**[2]**</a> Waloddi Weibull, “A Statistical Distribution Function of Wide Applicability”, Journal Of Applied Mechanics ASME Paper 1951.
* <a id='id3'>**[3]**</a> Wikipedia, “Weibull distribution”, [http://en.wikipedia.org/wiki/Weibull_distribution](http://en.wikipedia.org/wiki/Weibull_distribution)

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = 5. # shape
>>> s = mt.random.weibull(a, 1000)
```

Display the histogram of the samples, along with
the probability density function:

```pycon
>>> import matplotlib.pyplot as plt
>>> x = mt.arange(1,100.)/50.
>>> def weib(x,n,a):
...     return (a / n) * (x / n)**(a - 1) * mt.exp(-(x / n)**a)
```

```pycon
>>> count, bins, ignored = plt.hist(mt.random.weibull(5.,1000).execute())
>>> x = mt.arange(1,100.)/50.
>>> scale = count.max()/weib(x, 1., 5.).max()
>>> plt.plot(x.execute(), (weib(x, 1., 5.)*scale).execute())
>>> plt.show()
```
