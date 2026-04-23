# maxframe.tensor.take

### maxframe.tensor.take(a, indices, axis=None, out=None)

Take elements from a tensor along an axis.

When axis is not None, this function does the same thing as “fancy”
indexing (indexing arrays using tensors); however, it can be easier to use
if you need elements along a given axis. A call such as
`mt.take(arr, indices, axis=3)` is equivalent to
`arr[:,:,:,indices,...]`.

Explained without fancy indexing, this is equivalent to the following use
of ndindex, which sets each of `ii`, `jj`, and `kk` to a tuple of
indices:

```default
Ni, Nk = a.shape[:axis], a.shape[axis+1:]
Nj = indices.shape
for ii in ndindex(Ni):
    for jj in ndindex(Nj):
        for kk in ndindex(Nk):
            out[ii + jj + kk] = a[ii + (indices[jj],) + kk]
```

* **Parameters:**
  * **a** (*array_like* *(**Ni* *...* *,* *M* *,* *Nk* *...* *)*) – The source tensor.
  * **indices** (*array_like* *(**Nj* *...* *)*) – 

    The indices of the values to extract.

    Also allow scalars for indices.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The axis over which to select values. By default, the flattened
    input tensor is used.
  * **out** (*Tensor* *,* *optional* *(**Ni* *...* *,* *Nj* *...* *,* *Nk* *...* *)*) – If provided, the result will be placed in this tensor. It should
    be of the appropriate shape and dtype.
  * **mode** ( *{'raise'* *,*  *'wrap'* *,*  *'clip'}* *,* *optional*) – 

    Specifies how out-of-bounds indices will behave.
    * ’raise’ – raise an error (default)
    * ’wrap’ – wrap around
    * ’clip’ – clip to the range

    ’clip’ mode means that all indices that are too large are replaced
    by the index that addresses the last element along that axis. Note
    that this disables indexing with negative numbers.
* **Returns:**
  **out** – The returned tensor has the same type as a.
* **Return type:**
  Tensor (Ni…, Nj…, Nk…)

#### SEE ALSO
[`compress`](maxframe.tensor.compress.md#maxframe.tensor.compress)
: Take elements using a boolean mask

`Tensor.take`
: equivalent method

### Notes

By eliminating the inner loop in the description above, and using s_ to
build simple slice objects, take can be expressed  in terms of applying
fancy indexing to each 1-d slice:

```default
Ni, Nk = a.shape[:axis], a.shape[axis+1:]
for ii in ndindex(Ni):
    for kk in ndindex(Nj):
        out[ii + s_[...,] + kk] = a[ii + s_[:,] + kk][indices]
```

For this reason, it is equivalent to (but faster than) the following use
of apply_along_axis:

```default
out = mt.apply_along_axis(lambda a_1d: a_1d[indices], axis, a)
```

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> a = [4, 3, 5, 7, 6, 8]
>>> indices = [0, 1, 4]
>>> mt.take(a, indices).execute()
array([4, 3, 6])
```

In this example if a is a tensor, “fancy” indexing can be used.

```pycon
>>> a = mt.array(a)
>>> a[indices].execute()
array([4, 3, 6])
```

If indices is not one dimensional, the output also has these dimensions.

```pycon
>>> mt.take(a, [[0, 1], [2, 3]]).execute()
array([[4, 3],
       [5, 7]])
```
