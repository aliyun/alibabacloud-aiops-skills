# maxframe.tensor.random.f

### maxframe.tensor.random.f(dfnum, dfden, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from an F distribution.

Samples are drawn from an F distribution with specified parameters,
dfnum (degrees of freedom in numerator) and dfden (degrees of
freedom in denominator), where both parameters should be greater than
zero.

The random variate of the F distribution (also known as the
Fisher distribution) is a continuous probability distribution
that arises in ANOVA tests, and is the ratio of two chi-square
variates.

* **Parameters:**
  * **dfnum** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Degrees of freedom in numerator, should be > 0.
  * **dfden** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* [*float*](https://docs.python.org/3/library/functions.html#float)) – Degrees of freedom in denominator, should be > 0.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `dfnum` and `dfden` are both scalars.
    Otherwise, `np.broadcast(dfnum, dfden).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized Fisher distribution.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`scipy.stats.f`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.f.html#scipy.stats.f)
: probability density function, distribution or cumulative density function, etc.

### Notes

The F statistic is used to compare in-group variances to between-group
variances. Calculating the distribution depends on the sampling, and
so it is a function of the respective degrees of freedom in the
problem.  The variable dfnum is the number of samples minus one, the
between-groups degrees of freedom, while dfden is the within-groups
degrees of freedom, the sum of the number of samples in each group
minus the number of groups.

### References

* <a id='id1'>**[1]**</a> Glantz, Stanton A. “Primer of Biostatistics.”, McGraw-Hill, Fifth Edition, 2002.
* <a id='id2'>**[2]**</a> Wikipedia, “F-distribution”, [http://en.wikipedia.org/wiki/F-distribution](http://en.wikipedia.org/wiki/F-distribution)

### Examples

An example from Glantz[1], pp 47-40:

Two groups, children of diabetics (25 people) and children from people
without diabetes (25 controls). Fasting blood glucose was measured,
case group had a mean value of 86.1, controls had a mean value of
82.2. Standard deviations were 2.09 and 2.49 respectively. Are these
data consistent with the null hypothesis that the parents diabetic
status does not affect their children’s blood glucose levels?
Calculating the F statistic from the data gives a value of 36.01.

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> dfnum = 1. # between group degrees of freedom
>>> dfden = 48. # within groups degrees of freedom
>>> s = mt.random.f(dfnum, dfden, 1000).execute()
```

The lower bound for the top 1% of the samples is :

```pycon
>>> sorted(s)[-10]
7.61988120985
```

So there is about a 1% chance that the F statistic will exceed 7.62,
the measured value is 36, so the null hypothesis is rejected at the 1%
level.
