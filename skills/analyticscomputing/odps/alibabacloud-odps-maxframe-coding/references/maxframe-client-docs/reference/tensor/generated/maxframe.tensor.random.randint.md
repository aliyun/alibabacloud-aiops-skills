# maxframe.tensor.random.randint

### maxframe.tensor.random.randint(low, high=None, size=None, dtype='l', density=None, chunk_size=None, gpu=None)

Return random integers from low (inclusive) to high (exclusive).

Return random integers from the “discrete uniform” distribution of
the specified dtype in the “half-open” interval [low, high). If
high is None (the default), then results are from [0, low).

* **Parameters:**
  * **low** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Lowest (signed) integer to be drawn from the distribution (unless
    `high=None`, in which case this parameter is one above the
    *highest* such integer).
  * **high** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – If provided, one above the largest (signed) integer to be drawn
    from the distribution (see above for behavior if `high=None`).
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  Default is None, in which case a
    single value is returned.
  * **dtype** (*data-type* *,* *optional*) – Desired dtype of the result. All dtypes are determined by their
    name, i.e., ‘int64’, ‘int’, etc, so byteorder is not available
    and a specific precision may have different C types depending
    on the platform. The default value is ‘np.int’.
  * **density** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional*) – if density specified, a sparse tensor will be created
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** – Data-type of the returned tensor.
* **Returns:**
  **out** – size-shaped tensor of random integers from the appropriate
  distribution, or a single such random int if size not provided.
* **Return type:**
  [int](https://docs.python.org/3/library/functions.html#int) or Tensor of ints

#### SEE ALSO
`random.random_integers`
: similar to randint, only for the closed interval [low, high], and 1 is the lowest value if high is omitted. In particular, this other one is the one to use to generate uniformly distributed discrete non-integers.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.random.randint(2, size=10).execute()
array([1, 0, 0, 0, 1, 1, 0, 0, 1, 0])
>>> mt.random.randint(1, size=10).execute()
array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
```

Generate a 2 x 4 tensor of ints between 0 and 4, inclusive:

```pycon
>>> mt.random.randint(5, size=(2, 4)).execute()
array([[4, 0, 2, 1],
       [3, 2, 2, 0]])
```
