# maxframe.tensor.random.noncentral_f

### maxframe.tensor.random.noncentral_f(dfnum, dfden, nonc, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from the noncentral F distribution.

Samples are drawn from an F distribution with specified parameters,
dfnum (degrees of freedom in numerator) and dfden (degrees of
freedom in denominator), where both parameters > 1.
nonc is the non-centrality parameter.

* **Parameters:**
  * **dfnum** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Numerator degrees of freedom, should be > 0.
  * **dfden** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Denominator degrees of freedom, should be > 0.
  * **nonc** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Non-centrality parameter, the sum of the squares of the numerator
    means, should be >= 0.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `dfnum`, `dfden`, and `nonc`
    are all scalars.  Otherwise, `np.broadcast(dfnum, dfden, nonc).size`
    samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized noncentral Fisher distribution.
* **Return type:**
  Tensor or scalar

### Notes

When calculating the power of an experiment (power = probability of
rejecting the null hypothesis when a specific alternative is true) the
non-central F statistic becomes important.  When the null hypothesis is
true, the F statistic follows a central F distribution. When the null
hypothesis is not true, then it follows a non-central F statistic.

### References

* <a id='id1'>**[1]**</a> Weisstein, Eric W. “Noncentral F-Distribution.” From MathWorld–A Wolfram Web Resource. [http://mathworld.wolfram.com/NoncentralF-Distribution.html](http://mathworld.wolfram.com/NoncentralF-Distribution.html)
* <a id='id2'>**[2]**</a> Wikipedia, “Noncentral F-distribution”, [http://en.wikipedia.org/wiki/Noncentral_F-distribution](http://en.wikipedia.org/wiki/Noncentral_F-distribution)

### Examples

In a study, testing for a specific alternative to the null hypothesis
requires use of the Noncentral F distribution. We need to calculate the
area in the tail of the distribution that exceeds the value of the F
distribution for the null hypothesis.  We’ll plot the two probability
distributions for comparison.

```pycon
>>> import maxframe.tensor as mt
>>> import matplotlib.pyplot as plt
```

```pycon
>>> dfnum = 3 # between group deg of freedom
>>> dfden = 20 # within groups degrees of freedom
>>> nonc = 3.0
>>> nc_vals = mt.random.noncentral_f(dfnum, dfden, nonc, 1000000)
>>> NF = np.histogram(nc_vals.execute(), bins=50, normed=True)
>>> c_vals = mt.random.f(dfnum, dfden, 1000000)
>>> F = np.histogram(c_vals.execute(), bins=50, normed=True)
>>> plt.plot(F[1][1:], F[0])
>>> plt.plot(NF[1][1:], NF[0])
>>> plt.show()
```
