# maxframe.tensor.random.vonmises

### maxframe.tensor.random.vonmises(mu, kappa, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a von Mises distribution.

Samples are drawn from a von Mises distribution with specified mode
(mu) and dispersion (kappa), on the interval [-pi, pi].

The von Mises distribution (also known as the circular normal
distribution) is a continuous probability distribution on the unit
circle.  It may be thought of as the circular analogue of the normal
distribution.

* **Parameters:**
  * **mu** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Mode (“center”) of the distribution.
  * **kappa** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Dispersion of the distribution, has to be >=0.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `mu` and `kappa` are both scalars.
    Otherwise, `np.broadcast(mu, kappa).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized von Mises distribution.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`scipy.stats.vonmises`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.vonmises.html#scipy.stats.vonmises)
: probability density function, distribution, or cumulative density function, etc.

### Notes

The probability density for the von Mises distribution is

$$
p(x) = \frac{e^{\kappa cos(x-\mu)}}{2\pi I_0(\kappa)},

$$

where $\mu$ is the mode and $\kappa$ the dispersion,
and $I_0(\kappa)$ is the modified Bessel function of order 0.

The von Mises is named for Richard Edler von Mises, who was born in
Austria-Hungary, in what is now the Ukraine.  He fled to the United
States in 1939 and became a professor at Harvard.  He worked in
probability theory, aerodynamics, fluid mechanics, and philosophy of
science.

### References

* <a id='id1'>**[1]**</a> Abramowitz, M. and Stegun, I. A. (Eds.). “Handbook of Mathematical Functions with Formulas, Graphs, and Mathematical Tables, 9th printing,” New York: Dover, 1972.
* <a id='id2'>**[2]**</a> von Mises, R., “Mathematical Theory of Probability and Statistics”, New York: Academic Press, 1964.

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mu, kappa = 0.0, 4.0 # mean and dispersion
>>> s = mt.random.vonmises(mu, kappa, 1000)
```

Display the histogram of the samples, along with
the probability density function:

```pycon
>>> import matplotlib.pyplot as plt
>>> from scipy.special import i0
>>> plt.hist(s.execute(), 50, normed=True)
>>> x = mt.linspace(-mt.pi, mt.pi, num=51)
>>> y = mt.exp(kappa*mt.cos(x-mu))/(2*mt.pi*i0(kappa))
>>> plt.plot(x.execute(), y.execute(), linewidth=2, color='r')
>>> plt.show()
```
