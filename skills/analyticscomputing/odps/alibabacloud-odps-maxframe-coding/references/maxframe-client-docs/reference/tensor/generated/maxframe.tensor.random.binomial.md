# maxframe.tensor.random.binomial

### maxframe.tensor.random.binomial(n, p, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a binomial distribution.

Samples are drawn from a binomial distribution with specified
parameters, n trials and p probability of success where
n an integer >= 0 and p is in the interval [0,1]. (n may be
input as a float, but it is truncated to an integer in use)

* **Parameters:**
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *array_like* *of* *ints*) – Parameter of the distribution, >= 0. Floats are also accepted,
    but they will be truncated to integers.
  * **p** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Parameter of the distribution, >= 0 and <=1.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `n` and `p` are both scalars.
    Otherwise, `mt.broadcast(n, p).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized binomial distribution, where
  each sample is equal to the number of successes over the n trials.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`scipy.stats.binom`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binom.html#scipy.stats.binom)
: probability density function, distribution or cumulative density function, etc.

### Notes

The probability density for the binomial distribution is

$$
P(N) = \binom{n}{N}p^N(1-p)^{n-N},

$$

where $n$ is the number of trials, $p$ is the probability
of success, and $N$ is the number of successes.

When estimating the standard error of a proportion in a population by
using a random sample, the normal distribution works well unless the
product p\*n <=5, where p = population proportion estimate, and n =
number of samples, in which case the binomial distribution is used
instead. For example, a sample of 15 people shows 4 who are left
handed, and 11 who are right handed. Then p = 4/15 = 27%. 0.27\*15 = 4,
so the binomial distribution should be used in this case.

### References

* <a id='id1'>**[1]**</a> Dalgaard, Peter, “Introductory Statistics with R”, Springer-Verlag, 2002.
* <a id='id2'>**[2]**</a> Glantz, Stanton A. “Primer of Biostatistics.”, McGraw-Hill, Fifth Edition, 2002.
* <a id='id3'>**[3]**</a> Lentner, Marvin, “Elementary Applied Statistics”, Bogden and Quigley, 1972.
* <a id='id4'>**[4]**</a> Weisstein, Eric W. “Binomial Distribution.” From MathWorld–A Wolfram Web Resource. [http://mathworld.wolfram.com/BinomialDistribution.html](http://mathworld.wolfram.com/BinomialDistribution.html)
* <a id='id5'>**[5]**</a> Wikipedia, “Binomial distribution”, [http://en.wikipedia.org/wiki/Binomial_distribution](http://en.wikipedia.org/wiki/Binomial_distribution)

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> n, p = 10, .5  # number of trials, probability of each trial
>>> s = mt.random.binomial(n, p, 1000).execute()
# result of flipping a coin 10 times, tested 1000 times.
```

A real world example. A company drills 9 wild-cat oil exploration
wells, each with an estimated probability of success of 0.1. All nine
wells fail. What is the probability of that happening?

Let’s do 20,000 trials of the model, and count the number that
generate zero positive results.

```pycon
>>> (mt.sum(mt.random.binomial(9, 0.1, 20000) == 0)/20000.).execute()
# answer = 0.38885, or 38%.
```
