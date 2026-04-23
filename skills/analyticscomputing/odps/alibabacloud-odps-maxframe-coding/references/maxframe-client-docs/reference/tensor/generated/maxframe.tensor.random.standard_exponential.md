# maxframe.tensor.random.standard_exponential

### maxframe.tensor.random.standard_exponential(size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from the standard exponential distribution.

standard_exponential is identical to the exponential distribution
with a scale parameter of 1.

* **Parameters:**
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  Default is None, in which case a
    single value is returned.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples.
* **Return type:**
  [float](https://docs.python.org/3/library/functions.html#float) or Tensor

### Examples

Output a 3x8000 tensor:

```pycon
>>> import maxframe.tensor as mt
>>> n = mt.random.standard_exponential((3, 8000))
```
