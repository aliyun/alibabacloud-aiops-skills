# maxframe.tensor.random.random_integers

### maxframe.tensor.random.random_integers(low, high=None, size=None, chunk_size=None, gpu=None)

Random integers of type mt.int between low and high, inclusive.

Return random integers of type mt.int from the “discrete uniform”
distribution in the closed interval [low, high].  If high is
None (the default), then results are from [1, low]. The np.int
type translates to the C long type used by Python 2 for “short”
integers and its precision is platform dependent.

This function has been deprecated. Use randint instead.

* **Parameters:**
  * **low** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Lowest (signed) integer to be drawn from the distribution (unless
    `high=None`, in which case this parameter is the *highest* such
    integer).
  * **high** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – If provided, the largest (signed) integer to be drawn from the
    distribution (see above for behavior if `high=None`).
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  Default is None, in which case a
    single value is returned.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
* **Returns:**
  **out** – size-shaped array of random integers from the appropriate
  distribution, or a single such random int if size not provided.
* **Return type:**
  [int](https://docs.python.org/3/library/functions.html#int) or Tensor of ints

#### SEE ALSO
[`random.randint`](https://docs.python.org/3/library/random.html#random.randint)
: Similar to random_integers, only for the half-open interval [low, high), and 0 is the lowest value if high is omitted.

### Notes

To sample from N evenly spaced floating-point numbers between a and b,
use:

```default
a + (b - a) * (np.random.random_integers(N) - 1) / (N - 1.)
```

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.random.random_integers(5).execute()
4
>>> type(mt.random.random_integers(5).execute())
<type 'int'>
>>> mt.random.random_integers(5, size=(3,2)).execute()
array([[5, 4],
       [3, 3],
       [4, 5]])
```

Choose five random numbers from the set of five evenly-spaced
numbers between 0 and 2.5, inclusive (*i.e.*, from the set
${0, 5/8, 10/8, 15/8, 20/8}$):

```pycon
>>> (2.5 * (mt.random.random_integers(5, size=(5,)) - 1) / 4.).execute()
array([ 0.625,  1.25 ,  0.625,  0.625,  2.5  ])
```

Roll two six sided dice 1000 times and sum the results:

```pycon
>>> d1 = mt.random.random_integers(1, 6, 1000)
>>> d2 = mt.random.random_integers(1, 6, 1000)
>>> dsums = d1 + d2
```

Display results as a histogram:

```pycon
>>> import matplotlib.pyplot as plt
>>> count, bins, ignored = plt.hist(dsums.execute(), 11, normed=True)
>>> plt.show()
```
