# maxframe.tensor.fliplr

### maxframe.tensor.fliplr(m)

Flip tensor in the left/right direction.

Flip the entries in each row in the left/right direction.
Columns are preserved, but appear in a different order than before.

* **Parameters:**
  **m** (*array_like*) – Input tensor, must be at least 2-D.
* **Returns:**
  **f** – A view of m with the columns reversed.  Since a view
  is returned, this operation is $\mathcal O(1)$.
* **Return type:**
  Tensor

#### SEE ALSO
[`flipud`](maxframe.tensor.flipud.md#maxframe.tensor.flipud)
: Flip array in the up/down direction.

`rot90`
: Rotate array counterclockwise.

### Notes

Equivalent to m[:,::-1]. Requires the tensor to be at least 2-D.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> A = mt.diag([1.,2.,3.])
>>> A.execute()
array([[ 1.,  0.,  0.],
       [ 0.,  2.,  0.],
       [ 0.,  0.,  3.]])
>>> mt.fliplr(A).execute()
array([[ 0.,  0.,  1.],
       [ 0.,  2.,  0.],
       [ 3.,  0.,  0.]])
```

```pycon
>>> A = mt.random.randn(2,3,5)
>>> mt.all(mt.fliplr(A) == A[:,::-1,...]).execute()
True
```
