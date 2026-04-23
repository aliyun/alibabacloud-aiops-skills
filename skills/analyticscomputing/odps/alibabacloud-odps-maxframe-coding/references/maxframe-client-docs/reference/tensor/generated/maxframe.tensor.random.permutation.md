# maxframe.tensor.random.permutation

### maxframe.tensor.random.permutation(x, axis=0, chunk_size=None)

Randomly permute a sequence, or return a permuted range.

* **Parameters:**
  * **x** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *array_like*) – If x is an integer, randomly permute `mt.arange(x)`.
    If x is an array, make a copy and shuffle the elements
    randomly.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The axis which x is shuffled along. Default is 0.
  * **chunk_size** ( *: int* *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
* **Returns:**
  **out** – Permuted sequence or tensor range.
* **Return type:**
  Tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> rng = mt.random.RandomState()
>>> rng.permutation(10).execute()
array([1, 2, 3, 7, 9, 8, 0, 6, 4, 5]) # random
>>> rng.permutation([1, 4, 9, 12, 15]).execute()
array([ 9,  4, 12,  1, 15]) # random
>>> arr = mt.arange(9).reshape((3, 3))
>>> rng.permutation(arr).execute()
array([[3, 4, 5], # random
       [6, 7, 8],
       [0, 1, 2]])
>>> rng.permutation("abc")
Traceback (most recent call last):
    ...
numpy.AxisError: x must be an integer or at least 1-dimensional
```
