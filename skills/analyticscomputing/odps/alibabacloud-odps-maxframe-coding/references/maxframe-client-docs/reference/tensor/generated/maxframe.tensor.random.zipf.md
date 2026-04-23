# maxframe.tensor.random.zipf

### maxframe.tensor.random.zipf(a, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a Zipf distribution.

Samples are drawn from a Zipf distribution with specified parameter
a > 1.

The Zipf distribution (also known as the zeta distribution) is a
continuous probability distribution that satisfies Zipf’s law: the
frequency of an item is inversely proportional to its rank in a
frequency table.

* **Parameters:**
  * **a** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Distribution parameter. Should be greater than 1.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `a` is a scalar. Otherwise,
    `mt.array(a).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized Zipf distribution.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`scipy.stats.zipf`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.zipf.html#scipy.stats.zipf)
: probability density function, distribution, or cumulative density function, etc.

### Notes

The probability density for the Zipf distribution is

$$
p(x) = \frac{x^{-a}}{\zeta(a)},

$$

where $\zeta$ is the Riemann Zeta function.

It is named for the American linguist George Kingsley Zipf, who noted
that the frequency of any word in a sample of a language is inversely
proportional to its rank in the frequency table.

### References

* <a id='id1'>**[1]**</a> Zipf, G. K., “Selected Studies of the Principle of Relative Frequency in Language,” Cambridge, MA: Harvard Univ. Press, 1932.

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = 2. # parameter
>>> s = mt.random.zipf(a, 1000)
```

Display the histogram of the samples, along with
the probability density function:

```pycon
>>> import matplotlib.pyplot as plt
>>> from scipy import special
```

Truncate s values at 50 so plot is interesting:

```pycon
>>> count, bins, ignored = plt.hist(s[s<50].execute(), 50, normed=True)
>>> x = mt.arange(1., 50.)
>>> y = x**(-a) / special.zetac(a)
>>> plt.plot(x.execute(), (y/mt.max(y)).execute(), linewidth=2, color='r')
>>> plt.show()
```
