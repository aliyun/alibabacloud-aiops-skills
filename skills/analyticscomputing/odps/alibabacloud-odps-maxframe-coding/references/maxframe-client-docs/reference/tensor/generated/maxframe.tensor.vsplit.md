# maxframe.tensor.vsplit

### maxframe.tensor.vsplit(a, indices_or_sections)

Split a tensor into multiple sub-tensors vertically (row-wise).

Please refer to the `split` documentation.  `vsplit` is equivalent
to `split` with axis=0 (default), the tensor is always split along the
first axis regardless of the tensor dimension.

#### SEE ALSO
[`split`](maxframe.tensor.split.md#maxframe.tensor.split)
: Split a tensor into multiple sub-tensors of equal size.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.arange(16.0).reshape(4, 4)
>>> x.execute()
array([[  0.,   1.,   2.,   3.],
       [  4.,   5.,   6.,   7.],
       [  8.,   9.,  10.,  11.],
       [ 12.,  13.,  14.,  15.]])
>>> mt.vsplit(x, 2).execute()
[array([[ 0.,  1.,  2.,  3.],
       [ 4.,  5.,  6.,  7.]]),
 array([[  8.,   9.,  10.,  11.],
       [ 12.,  13.,  14.,  15.]])]
>>> mt.vsplit(x, mt.array([3, 6])).execute()
[array([[  0.,   1.,   2.,   3.],
       [  4.,   5.,   6.,   7.],
       [  8.,   9.,  10.,  11.]]),
 array([[ 12.,  13.,  14.,  15.]]),
 array([], dtype=float64)]
```

With a higher dimensional tensor the split is still along the first axis.

```pycon
>>> x = mt.arange(8.0).reshape(2, 2, 2)
>>> x.execute()
array([[[ 0.,  1.],
        [ 2.,  3.]],
       [[ 4.,  5.],
        [ 6.,  7.]]])
>>> mt.vsplit(x, 2).execute()
[array([[[ 0.,  1.],
        [ 2.,  3.]]]),
 array([[[ 4.,  5.],
        [ 6.,  7.]]])]
```
