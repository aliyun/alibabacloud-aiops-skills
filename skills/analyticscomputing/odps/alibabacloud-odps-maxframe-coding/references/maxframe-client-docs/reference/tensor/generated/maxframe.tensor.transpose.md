# maxframe.tensor.transpose

### maxframe.tensor.transpose(a, axes=None)

Returns an array with axes transposed.

For a 1-D array, this returns an unchanged view of the original array, as a
transposed vector is simply the same vector.
To convert a 1-D array into a 2-D column vector, an additional dimension
must be added, e.g., `mt.atleast_2d(a).T` achieves this, as does
`a[:, mt.newaxis]`.
For a 2-D array, this is the standard matrix transpose.
For an n-D array, if axes are given, their order indicates how the
axes are permuted (see Examples). If axes are not provided, then
`transpose(a).shape == a.shape[::-1]`.

* **Parameters:**
  * **a** (*array_like*) – Input array.
  * **axes** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *ints* *,* *optional*) – If specified, it must be a tuple or list which contains a permutation
    of [0,1,…,N-1] where N is the number of axes of a. The i’th axis
    of the returned array will correspond to the axis numbered `axes[i]`
    of the input. If not specified, defaults to `range(a.ndim)[::-1]`,
    which reverses the order of the axes.
* **Returns:**
  **p** – a with its axes permuted. A view is returned whenever possible.
* **Return type:**
  ndarray

### Notes

Use `transpose(a, argsort(axes))` to invert the transposition of tensors
when using the axes keyword argument.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.arange(4).reshape((2,2))
>>> x.execute()
array([[0, 1],
       [2, 3]])
```

```pycon
>>> mt.transpose(x).execute()
array([[0, 2],
       [1, 3]])
```

```pycon
>>> x = mt.ones((1, 2, 3))
>>> mt.transpose(x, (1, 0, 2)).shape
(2, 1, 3)
```
