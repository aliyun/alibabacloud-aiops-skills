# maxframe.tensor.random.noncentral_chisquare

### maxframe.tensor.random.noncentral_chisquare(df, nonc, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a noncentral chi-square distribution.

The noncentral $\chi^2$ distribution is a generalisation of
the $\chi^2$ distribution.

* **Parameters:**
  * **df** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Degrees of freedom, should be > 0.
  * **nonc** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Non-centrality, should be non-negative.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `df` and `nonc` are both scalars.
    Otherwise, `mt.broadcast(df, nonc).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized noncentral chi-square distribution.
* **Return type:**
  Tensor or scalar

### Notes

The probability density function for the noncentral Chi-square
distribution is

$$
P(x;df,nonc) = \sum^{\infty}_{i=0}
\frac{e^{-nonc/2}(nonc/2)^{i}}{i!}
\P_{Y_{df+2i}}(x),

$$

where $Y_{q}$ is the Chi-square with q degrees of freedom.

In Delhi (2007), it is noted that the noncentral chi-square is
useful in bombing and coverage problems, the probability of
killing the point target given by the noncentral chi-squared
distribution.

### References

* <a id='id1'>**[1]**</a> Delhi, M.S. Holla, “On a noncentral chi-square distribution in the analysis of weapon systems effectiveness”, Metrika, Volume 15, Number 1 / December, 1970.
* <a id='id2'>**[2]**</a> Wikipedia, “Noncentral chi-square distribution” [http://en.wikipedia.org/wiki/Noncentral_chi-square_distribution](http://en.wikipedia.org/wiki/Noncentral_chi-square_distribution)

### Examples

Draw values from the distribution and plot the histogram

```pycon
>>> import matplotlib.pyplot as plt
>>> import maxframe.tensor as mt
>>> values = plt.hist(mt.random.noncentral_chisquare(3, 20, 100000).execute(),
...                   bins=200, normed=True)
>>> plt.show()
```

Draw values from a noncentral chisquare with very small noncentrality,
and compare to a chisquare.

```pycon
>>> plt.figure()
>>> values = plt.hist(mt.random.noncentral_chisquare(3, .0000001, 100000).execute(),
...                   bins=mt.arange(0., 25, .1).execute(), normed=True)
>>> values2 = plt.hist(mt.random.chisquare(3, 100000).execute(),
...                    bins=mt.arange(0., 25, .1).execute(), normed=True)
>>> plt.plot(values[1][0:-1], values[0]-values2[0], 'ob')
>>> plt.show()
```

Demonstrate how large values of non-centrality lead to a more symmetric
distribution.

```pycon
>>> plt.figure()
>>> values = plt.hist(mt.random.noncentral_chisquare(3, 20, 100000).execute(),
...                   bins=200, normed=True)
>>> plt.show()
```
