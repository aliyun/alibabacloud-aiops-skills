# maxframe.tensor.random.sample

### maxframe.tensor.random.sample(size=None, chunk_size=None, gpu=None, dtype=None)

Return random floats in the half-open interval [0.0, 1.0).

Results are from the “continuous uniform” distribution over the
stated interval.  To sample $Unif[a, b), b > a$ multiply
the output of random_sample by (b-a) and add a:

```default
(b - a) * random_sample() + a
```

* **Parameters:**
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  Default is None, in which case a
    single value is returned.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Array of random floats of shape size (unless `size=None`, in which
  case a single float is returned).
* **Return type:**
  [float](https://docs.python.org/3/library/functions.html#float) or Tensor of floats

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.random.random_sample().execute()
0.47108547995356098
>>> type(mt.random.random_sample().execute())
<type 'float'>
>>> mt.random.random_sample((5,)).execute()
array([ 0.30220482,  0.86820401,  0.1654503 ,  0.11659149,  0.54323428])
```

Three-by-two array of random numbers from [-5, 0):

```pycon
>>> (5 * mt.random.random_sample((3, 2)) - 5).execute()
array([[-3.99149989, -0.52338984],
       [-2.99091858, -0.79479508],
       [-1.23204345, -1.75224494]])
```
