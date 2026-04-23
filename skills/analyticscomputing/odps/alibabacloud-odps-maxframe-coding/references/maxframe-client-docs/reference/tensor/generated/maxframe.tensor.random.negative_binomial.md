# maxframe.tensor.random.negative_binomial

### maxframe.tensor.random.negative_binomial(n, p, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a negative binomial distribution.

Samples are drawn from a negative binomial distribution with specified
parameters, n trials and p probability of success where n is an
integer > 0 and p is in the interval [0, 1].

* **Parameters:**
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *array_like* *of* *ints*) – Parameter of the distribution, > 0. Floats are also accepted,
    but they will be truncated to integers.
  * **p** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Parameter of the distribution, >= 0 and <=1.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `n` and `p` are both scalars.
    Otherwise, `np.broadcast(n, p).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized negative binomial distribution,
  where each sample is equal to N, the number of trials it took to
  achieve n - 1 successes, N - (n - 1) failures, and a success on the,
  (N + n)th trial.
* **Return type:**
  Tensor or scalar

### Notes

The probability density for the negative binomial distribution is

$$
P(N;n,p) = \binom{N+n-1}{n-1}p^{n}(1-p)^{N},

$$

where $n-1$ is the number of successes, $p$ is the
probability of success, and $N+n-1$ is the number of trials.
The negative binomial distribution gives the probability of n-1
successes and N failures in N+n-1 trials, and success on the (N+n)th
trial.

If one throws a die repeatedly until the third time a “1” appears,
then the probability distribution of the number of non-“1”s that
appear before the third “1” is a negative binomial distribution.

### References

* <a id='id1'>**[1]**</a> Weisstein, Eric W. “Negative Binomial Distribution.” From MathWorld–A Wolfram Web Resource. [http://mathworld.wolfram.com/NegativeBinomialDistribution.html](http://mathworld.wolfram.com/NegativeBinomialDistribution.html)
* <a id='id2'>**[2]**</a> Wikipedia, “Negative binomial distribution”, [http://en.wikipedia.org/wiki/Negative_binomial_distribution](http://en.wikipedia.org/wiki/Negative_binomial_distribution)

### Examples

Draw samples from the distribution:

A real world example. A company drills wild-cat oil
exploration wells, each with an estimated probability of
success of 0.1.  What is the probability of having one success
for each successive well, that is what is the probability of a
single success after drilling 5 wells, after 6 wells, etc.?

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> s = mt.random.negative_binomial(1, 0.1, 100000)
>>> for i in range(1, 11):
...    probability = (mt.sum(s<i) / 100000.).execute()
...    print i, "wells drilled, probability of one success =", probability
```
