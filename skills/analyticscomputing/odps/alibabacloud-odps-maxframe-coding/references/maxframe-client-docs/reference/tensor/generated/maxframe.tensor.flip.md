# maxframe.tensor.flip

### maxframe.tensor.flip(m, axis)

Reverse the order of elements in a tensor along the given axis.

The shape of the array is preserved, but the elements are reordered.

* **Parameters:**
  * **m** (*array_like*) – Input tensor.
  * **axis** (*integer*) – Axis in tensor, which entries are reversed.
* **Returns:**
  **out** – A view of m with the entries of axis reversed.  Since a view is
  returned, this operation is done in constant time.
* **Return type:**
  array_like

#### SEE ALSO
[`flipud`](maxframe.tensor.flipud.md#maxframe.tensor.flipud)
: Flip a tensor vertically (axis=0).

[`fliplr`](maxframe.tensor.fliplr.md#maxframe.tensor.fliplr)
: Flip a tensor horizontally (axis=1).

### Notes

flip(m, 0) is equivalent to flipud(m).
flip(m, 1) is equivalent to fliplr(m).
flip(m, n) corresponds to `m[...,::-1,...]` with `::-1` at position n.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> A = mt.arange(8).reshape((2,2,2))
>>> A.execute()
array([[[0, 1],
        [2, 3]],
```

> [[4, 5],
> : [6, 7]]])
```pycon
>>> mt.flip(A, 0).execute()
array([[[4, 5],
        [6, 7]],
```

> [[0, 1],
> : [2, 3]]])
```pycon
>>> mt.flip(A, 1).execute()
array([[[2, 3],
        [0, 1]],
```

> [[6, 7],
> : [4, 5]]])
```pycon
>>> A = mt.random.randn(3,4,5)
>>> mt.all(mt.flip(A,2) == A[:,:,::-1,...]).execute()
True
```
