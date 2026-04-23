# maxframe.tensor.random.multinomial

### maxframe.tensor.random.multinomial(n, pvals, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a multinomial distribution.

The multinomial distribution is a multivariate generalisation of the
binomial distribution.  Take an experiment with one of `p`
possible outcomes.  An example of such an experiment is throwing a dice,
where the outcome can be 1 through 6.  Each sample drawn from the
distribution represents n such experiments.  Its values,
`X_i = [X_0, X_1, ..., X_p]`, represent the number of times the
outcome was `i`.

* **Parameters:**
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Number of experiments.
  * **pvals** (*sequence* *of* *floats* *,* *length p*) – Probabilities of each of the `p` different outcomes.  These
    should sum to 1 (however, the last element is always assumed to
    account for the remaining probability, as long as
    `sum(pvals[:-1]) <= 1)`.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  Default is None, in which case a
    single value is returned.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – The drawn samples, of shape *size*, if that was provided.  If not,
  the shape is `(N,)`.

  In other words, each entry `out[i,j,...,:]` is an N-dimensional
  value drawn from the distribution.
* **Return type:**
  Tensor

### Examples

Throw a dice 20 times:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.random.multinomial(20, [1/6.]*6, size=1).execute()
array([[4, 1, 7, 5, 2, 1]])
```

It landed 4 times on 1, once on 2, etc.

Now, throw the dice 20 times, and 20 times again:

```pycon
>>> mt.random.multinomial(20, [1/6.]*6, size=2).execute()
array([[3, 4, 3, 3, 4, 3],
       [2, 4, 3, 4, 0, 7]])
```

For the first run, we threw 3 times 1, 4 times 2, etc.  For the second,
we threw 2 times 1, 4 times 2, etc.

A loaded die is more likely to land on number 6:

```pycon
>>> mt.random.multinomial(100, [1/7.]*5 + [2/7.]).execute()
array([11, 16, 14, 17, 16, 26])
```

The probability inputs should be normalized. As an implementation
detail, the value of the last entry is ignored and assumed to take
up any leftover probability mass, but this should not be relied on.
A biased coin which has twice as much weight on one side as on the
other should be sampled like so:

```pycon
>>> mt.random.multinomial(100, [1.0 / 3, 2.0 / 3]).execute()  # RIGHT
array([38, 62])
```

not like:

```pycon
>>> mt.random.multinomial(100, [1.0, 2.0]).execute()  # WRONG
array([100,   0])
```
