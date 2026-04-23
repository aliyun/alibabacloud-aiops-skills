# maxframe.tensor.random.uniform

### maxframe.tensor.random.uniform(low=0.0, high=1.0, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a uniform distribution.

Samples are uniformly distributed over the half-open interval
`[low, high)` (includes low, but excludes high).  In other words,
any value within the given interval is equally likely to be drawn
by uniform.

* **Parameters:**
  * **low** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats* *,* *optional*) – Lower boundary of the output interval.  All values generated will be
    greater than or equal to low.  The default value is 0.
  * **high** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Upper boundary of the output interval.  All values generated will be
    less than high.  The default value is 1.0.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `low` and `high` are both scalars.
    Otherwise, `mt.broadcast(low, high).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized uniform distribution.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`randint`](maxframe.tensor.random.randint.md#maxframe.tensor.random.randint)
: Discrete uniform distribution, yielding integers.

[`random_integers`](maxframe.tensor.random.random_integers.md#maxframe.tensor.random.random_integers)
: Discrete uniform distribution over the closed interval `[low, high]`.

[`random_sample`](maxframe.tensor.random.random_sample.md#maxframe.tensor.random.random_sample)
: Floats uniformly distributed over `[0, 1)`.

[`random`](maxframe.tensor.random.random.md#maxframe.tensor.random.random)
: Alias for random_sample.

[`rand`](maxframe.tensor.random.rand.md#maxframe.tensor.random.rand)
: Convenience function that accepts dimensions as input, e.g., `rand(2,2)` would generate a 2-by-2 array of floats, uniformly distributed over `[0, 1)`.

### Notes

The probability density function of the uniform distribution is

$$
p(x) = \frac{1}{b - a}

$$

anywhere within the interval `[a, b)`, and zero elsewhere.

When `high` == `low`, values of `low` will be returned.
If `high` < `low`, the results are officially undefined
and may eventually raise an error, i.e. do not rely on this
function to behave when passed arguments satisfying that
inequality condition.

### Examples

Draw samples from the distribution:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> s = mt.random.uniform(-1,0,1000)
```

All values are within the given interval:

```pycon
>>> mt.all(s >= -1).execute()
True
>>> mt.all(s < 0).execute()
True
```

Display the histogram of the samples, along with the
probability density function:

```pycon
>>> import matplotlib.pyplot as plt
>>> count, bins, ignored = plt.hist(s.execute(), 15, normed=True)
>>> plt.plot(bins, mt.ones_like(bins).execute(), linewidth=2, color='r')
>>> plt.show()
```
