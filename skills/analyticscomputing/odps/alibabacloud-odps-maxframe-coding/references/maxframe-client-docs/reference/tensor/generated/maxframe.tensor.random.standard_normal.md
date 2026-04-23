# maxframe.tensor.random.standard_normal

### maxframe.tensor.random.standard_normal(size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a standard Normal distribution (mean=0, stdev=1).

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

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> s = mt.random.standard_normal(8000)
>>> s.execute()
array([ 0.6888893 ,  0.78096262, -0.89086505, ...,  0.49876311, #random
       -0.38672696, -0.4685006 ])                               #random
>>> s.shape
(8000,)
>>> s = mt.random.standard_normal(size=(3, 4, 2))
>>> s.shape
(3, 4, 2)
```
