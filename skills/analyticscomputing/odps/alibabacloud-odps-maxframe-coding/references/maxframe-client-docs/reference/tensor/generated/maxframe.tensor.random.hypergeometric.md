# maxframe.tensor.random.hypergeometric

### maxframe.tensor.random.hypergeometric(ngood, nbad, nsample, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a Hypergeometric distribution.

Samples are drawn from a hypergeometric distribution with specified
parameters, ngood (ways to make a good selection), nbad (ways to make
a bad selection), and nsample = number of items sampled, which is less
than or equal to the sum ngood + nbad.

* **Parameters:**
  * **ngood** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *array_like* *of* *ints*) – Number of ways to make a good selection.  Must be nonnegative.
  * **nbad** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *array_like* *of* *ints*) – Number of ways to make a bad selection.  Must be nonnegative.
  * **nsample** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *array_like* *of* *ints*) – Number of items sampled.  Must be at least 1 and at most
    `ngood + nbad`.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `ngood`, `nbad`, and `nsample`
    are all scalars.  Otherwise, `np.broadcast(ngood, nbad, nsample).size`
    samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized hypergeometric distribution.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`scipy.stats.hypergeom`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.hypergeom.html#scipy.stats.hypergeom)
: probability density function, distribution or cumulative density function, etc.

### Notes

The probability density for the Hypergeometric distribution is

$$
P(x) = \frac{\binom{m}{n}\binom{N-m}{n-x}}{\binom{N}{n}},

$$

where $0 \le x \le m$ and $n+m-N \le x \le n$

for P(x) the probability of x successes, n = ngood, m = nbad, and
N = number of samples.

Consider an urn with black and white marbles in it, ngood of them
black and nbad are white. If you draw nsample balls without
replacement, then the hypergeometric distribution describes the
distribution of black balls in the drawn sample.

Note that this distribution is very similar to the binomial
distribution, except that in this case, samples are drawn without
replacement, whereas in the Binomial case samples are drawn with
replacement (or the sample space is infinite). As the sample space
becomes large, this distribution approaches the binomial.

### References

* <a id='id1'>**[1]**</a> Lentner, Marvin, “Elementary Applied Statistics”, Bogden and Quigley, 1972.
* <a id='id2'>**[2]**</a> Weisstein, Eric W. “Hypergeometric Distribution.” From MathWorld–A Wolfram Web Resource. [http://mathworld.wolfram.com/HypergeometricDistribution.html](http://mathworld.wolfram.com/HypergeometricDistribution.html)
* <a id='id3'>**[3]**</a> Wikipedia, “Hypergeometric distribution”, [http://en.wikipedia.org/wiki/Hypergeometric_distribution](http://en.wikipedia.org/wiki/Hypergeometric_distribution)

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> ngood, nbad, nsamp = 100, 2, 10
# number of good, number of bad, and number of samples
>>> s = mt.random.hypergeometric(ngood, nbad, nsamp, 1000)
>>> hist(s)
#   note that it is very unlikely to grab both bad items
```

Suppose you have an urn with 15 white and 15 black marbles.
If you pull 15 marbles at random, how likely is it that
12 or more of them are one color?

```pycon
>>> s = mt.random.hypergeometric(15, 15, 15, 100000)
>>> (mt.sum(s>=12)/100000. + mt.sum(s<=3)/100000.).execute()
#   answer = 0.003 ... pretty unlikely!
```
