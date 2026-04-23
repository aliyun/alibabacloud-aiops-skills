# maxframe.tensor.random.geometric

### maxframe.tensor.random.geometric(p, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from the geometric distribution.

Bernoulli trials are experiments with one of two outcomes:
success or failure (an example of such an experiment is flipping
a coin).  The geometric distribution models the number of trials
that must be run in order to achieve success.  It is therefore
supported on the positive integers, `k = 1, 2, ...`.

The probability mass function of the geometric distribution is

$$
f(k) = (1 - p)^{k - 1} p

$$

where p is the probability of success of an individual trial.

* **Parameters:**
  * **p** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – The probability of success of an individual trial.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `p` is a scalar.  Otherwise,
    `mt.array(p).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized geometric distribution.
* **Return type:**
  Tensor or scalar

### Examples

Draw ten thousand values from the geometric distribution,
with the probability of an individual success equal to 0.35:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> z = mt.random.geometric(p=0.35, size=10000)
```

How many trials succeeded after a single run?

```pycon
>>> ((z == 1).sum() / 10000.).execute()
0.34889999999999999 #random
```
