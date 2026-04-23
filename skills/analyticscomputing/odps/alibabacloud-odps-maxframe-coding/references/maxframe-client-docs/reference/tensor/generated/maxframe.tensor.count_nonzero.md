# maxframe.tensor.count_nonzero

### maxframe.tensor.count_nonzero(a, axis=None)

Counts the number of non-zero values in the tensor `a`.

The word “non-zero” is in reference to the Python 2.x
built-in method `__nonzero__()` (renamed `__bool__()`
in Python 3.x) of Python objects that tests an object’s
“truthfulness”. For example, any number is considered
truthful if it is nonzero, whereas any string is considered
truthful if it is not the empty string. Thus, this function
(recursively) counts how many elements in `a` (and in
sub-tensors thereof) have their `__nonzero__()` or `__bool__()`
method evaluated to `True`.

* **Parameters:**
  * **a** (*array_like*) – The tensor for which to count non-zeros.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *,* *optional*) – Axis or tuple of axes along which to count non-zeros.
    Default is None, meaning that non-zeros will be counted
    along a flattened version of `a`.
* **Returns:**
  **count** – Number of non-zero values in the array along a given axis.
  Otherwise, the total number of non-zero values in the tensor
  is returned.
* **Return type:**
  [int](https://docs.python.org/3/library/functions.html#int) or tensor of [int](https://docs.python.org/3/library/functions.html#int)

#### SEE ALSO
[`nonzero`](maxframe.tensor.nonzero.md#maxframe.tensor.nonzero)
: Return the coordinates of all the non-zero values.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.count_nonzero(mt.eye(4)).execute()
4
>>> mt.count_nonzero([[0,1,7,0,0],[3,0,0,2,19]]).execute()
5
>>> mt.count_nonzero([[0,1,7,0,0],[3,0,0,2,19]], axis=0).execute()
array([1, 1, 1, 1, 1])
>>> mt.count_nonzero([[0,1,7,0,0],[3,0,0,2,19]], axis=1).execute()
array([2, 3])
```
