# maxframe.tensor.random.logseries

### maxframe.tensor.random.logseries(p, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a logarithmic series distribution.

Samples are drawn from a log series distribution with specified
shape parameter, 0 < `p` < 1.

* **Parameters:**
  * **p** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Shape parameter for the distribution.  Must be in the range (0, 1).
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `p` is a scalar.  Otherwise,
    `np.array(p).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized logarithmic series distribution.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`scipy.stats.logser`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.logser.html#scipy.stats.logser)
: probability density function, distribution or cumulative density function, etc.

### Notes

The probability density for the Log Series distribution is

$$
P(k) = \frac{-p^k}{k \ln(1-p)},

$$

where p = probability.

The log series distribution is frequently used to represent species
richness and occurrence, first proposed by Fisher, Corbet, and
Williams in 1943 [2].  It may also be used to model the numbers of
occupants seen in cars [3].

### References

* <a id='id1'>**[1]**</a> Buzas, Martin A.; Culver, Stephen J.,  Understanding regional species diversity through the log series distribution of occurrences: BIODIVERSITY RESEARCH Diversity & Distributions, Volume 5, Number 5, September 1999 , pp. 187-195(9).
* <a id='id2'>**[2]**</a> Fisher, R.A,, A.S. Corbet, and C.B. Williams. 1943. The relation between the number of species and the number of individuals in a random sample of an animal population. Journal of Animal Ecology, 12:42-58.
* <a id='id3'>**[3]**</a> D. J. Hand, F. Daly, D. Lunn, E. Ostrowski, A Handbook of Small Data Sets, CRC Press, 1994.
* <a id='id4'>**[4]**</a> Wikipedia, “Logarithmic distribution”, [http://en.wikipedia.org/wiki/Logarithmic_distribution](http://en.wikipedia.org/wiki/Logarithmic_distribution)

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
>>> import matplotlib.pyplot as plt
```

```pycon
>>> a = .6
>>> s = mt.random.logseries(a, 10000)
>>> count, bins, ignored = plt.hist(s.execute())
```

#   plot against distribution

```pycon
>>> def logseries(k, p):
...     return -p**k/(k*mt.log(1-p))
>>> plt.plot(bins, (logseries(bins, a)*count.max()/
...          logseries(bins, a).max()).execute(), 'r')
>>> plt.show()
```
