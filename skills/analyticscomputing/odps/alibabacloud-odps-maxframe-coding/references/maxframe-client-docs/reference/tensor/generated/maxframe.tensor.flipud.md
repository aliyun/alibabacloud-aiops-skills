# maxframe.tensor.flipud

### maxframe.tensor.flipud(m)

Flip tensor in the up/down direction.

Flip the entries in each column in the up/down direction.
Rows are preserved, but appear in a different order than before.

* **Parameters:**
  **m** (*array_like*) – Input tensor.
* **Returns:**
  **out** – A view of m with the rows reversed.  Since a view is
  returned, this operation is $\mathcal O(1)$.
* **Return type:**
  array_like

#### SEE ALSO
[`fliplr`](maxframe.tensor.fliplr.md#maxframe.tensor.fliplr)
: Flip tensor in the left/right direction.

`rot90`
: Rotate tensor counterclockwise.

### Notes

Equivalent to `m[::-1,...]`.
Does not require the tensor to be two-dimensional.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> A = mt.diag([1.0, 2, 3])
>>> A.execute()
array([[ 1.,  0.,  0.],
       [ 0.,  2.,  0.],
       [ 0.,  0.,  3.]])
>>> mt.flipud(A).execute()
array([[ 0.,  0.,  3.],
       [ 0.,  2.,  0.],
       [ 1.,  0.,  0.]])
```

```pycon
>>> A = mt.random.randn(2,3,5)
>>> mt.all(mt.flipud(A) == A[::-1,...]).execute()
True
```

```pycon
>>> mt.flipud([1,2]).execute()
array([2, 1])
```
