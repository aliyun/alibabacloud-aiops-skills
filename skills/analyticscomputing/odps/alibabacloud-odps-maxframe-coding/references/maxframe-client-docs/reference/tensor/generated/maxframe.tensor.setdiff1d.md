# maxframe.tensor.setdiff1d

### maxframe.tensor.setdiff1d(ar1, ar2, assume_unique=False)

Find the set difference of two tensors.

Return the unique values in ar1 that are not in ar2.

* **Parameters:**
  * **ar1** (*array_like*) – Input tensor.
  * **ar2** (*array_like*) – Input comparison tensor.
  * **assume_unique** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – If True, the input tensors are both assumed to be unique, which
    can speed up the calculation.  Default is False.
* **Returns:**
  **setdiff1d** – 1D tensor of values in ar1 that are not in ar2. The result
  is sorted when assume_unique=False, but otherwise only sorted
  if the input is sorted.
* **Return type:**
  Tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> a = mt.array([1, 2, 3, 2, 4, 1])
>>> b = mt.array([3, 4, 5, 6])
>>> mt.setdiff1d(a, b).execute()
array([1, 2])
```
