# maxframe.tensor.random.power

### maxframe.tensor.random.power(a, size=None, chunk_size=None, gpu=None, dtype=None)

Draws samples in [0, 1] from a power distribution with positive
exponent a - 1.

Also known as the power function distribution.

* **Parameters:**
  * **a** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Parameter of the distribution. Should be greater than zero.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `a` is a scalar.  Otherwise,
    `mt.array(a).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized power distribution.
* **Return type:**
  Tensor or scalar
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If a < 1.

### Notes

The probability density function is

$$
P(x; a) = ax^{a-1}, 0 \le x \le 1, a>0.

$$

The power function distribution is just the inverse of the Pareto
distribution. It may also be seen as a special case of the Beta
distribution.

It is used, for example, in modeling the over-reporting of insurance
claims.

### References

* <a id='id1'>**[1]**</a> Christian Kleiber, Samuel Kotz, “Statistical size distributions in economics and actuarial sciences”, Wiley, 2003.
* <a id='id2'>**[2]**</a> Heckert, N. A. and Filliben, James J. “NIST Handbook 148: Dataplot Reference Manual, Volume 2: Let Subcommands and Library Functions”, National Institute of Standards and Technology Handbook Series, June 2003. [http://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/powpdf.pdf](http://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/powpdf.pdf)

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = 5. # shape
>>> samples = 1000
>>> s = mt.random.power(a, samples)
```

Display the histogram of the samples, along with
the probability density function:

```pycon
>>> import matplotlib.pyplot as plt
>>> count, bins, ignored = plt.hist(s.execute(), bins=30)
>>> x = mt.linspace(0, 1, 100)
>>> y = a*x**(a-1.)
>>> normed_y = samples*mt.diff(bins)[0]*y
>>> plt.plot(x.execute(), normed_y.execute())
>>> plt.show()
```

Compare the power function distribution to the inverse of the Pareto.

```pycon
>>> from scipy import stats
>>> rvs = mt.random.power(5, 1000000)
>>> rvsp = mt.random.pareto(5, 1000000)
>>> xx = mt.linspace(0,1,100)
>>> powpdf = stats.powerlaw.pdf(xx.execute(),5)
```

```pycon
>>> plt.figure()
>>> plt.hist(rvs.execute(), bins=50, normed=True)
>>> plt.plot(xx.execute(),powpdf,'r-')
>>> plt.title('np.random.power(5)')
```

```pycon
>>> plt.figure()
>>> plt.hist((1./(1.+rvsp)).execute(), bins=50, normed=True)
>>> plt.plot(xx.execute(),powpdf,'r-')
>>> plt.title('inverse of 1 + np.random.pareto(5)')
```

```pycon
>>> plt.figure()
>>> plt.hist((1./(1.+rvsp)).execute(), bins=50, normed=True)
>>> plt.plot(xx.execute(),powpdf,'r-')
>>> plt.title('inverse of stats.pareto(5)')
```
