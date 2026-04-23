# maxframe.tensor.hsplit

### maxframe.tensor.hsplit(a, indices_or_sections)

Split a tensor into multiple sub-tensors horizontally (column-wise).

Please refer to the split documentation.  hsplit is equivalent
to split with `axis=1`, the tensor is always split along the second
axis regardless of the tensor dimension.

#### SEE ALSO
[`split`](maxframe.tensor.split.md#maxframe.tensor.split)
: Split an array into multiple sub-arrays of equal size.

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
>>> mt.hsplit(x, 2).execute()
[array([[  0.,   1.],
       [  4.,   5.],
       [  8.,   9.],
       [ 12.,  13.]]),
 array([[  2.,   3.],
       [  6.,   7.],
       [ 10.,  11.],
       [ 14.,  15.]])]
>>> mt.hsplit(x, mt.array([3, 6])).execute()
[array([[  0.,   1.,   2.],
       [  4.,   5.,   6.],
       [  8.,   9.,  10.],
       [ 12.,  13.,  14.]]),
 array([[  3.],
       [  7.],
       [ 11.],
       [ 15.]]),
 array([], dtype=float64)]
```

With a higher dimensional array the split is still along the second axis.

```pycon
>>> x = mt.arange(8.0).reshape(2, 2, 2)
>>> x.execute()
array([[[ 0.,  1.],
        [ 2.,  3.]],
       [[ 4.,  5.],
        [ 6.,  7.]]])
>>> mt.hsplit(x, 2)
[array([[[ 0.,  1.]],
       [[ 4.,  5.]]]),
 array([[[ 2.,  3.]],
       [[ 6.,  7.]]])]
```
