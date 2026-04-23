# maxframe.tensor.dsplit

### maxframe.tensor.dsplit(a, indices_or_sections)

Split tensor into multiple sub-tensors along the 3rd axis (depth).

Please refer to the split documentation.  dsplit is equivalent
to split with `axis=2`, the array is always split along the third
axis provided the tensor dimension is greater than or equal to 3.

#### SEE ALSO
[`split`](maxframe.tensor.split.md#maxframe.tensor.split)
: Split a tensor into multiple sub-arrays of equal size.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.arange(16.0).reshape(2, 2, 4)
>>> x.execute()
array([[[  0.,   1.,   2.,   3.],
        [  4.,   5.,   6.,   7.]],
       [[  8.,   9.,  10.,  11.],
        [ 12.,  13.,  14.,  15.]]])
>>> mt.dsplit(x, 2).execute()
[array([[[  0.,   1.],
        [  4.,   5.]],
       [[  8.,   9.],
        [ 12.,  13.]]]),
 array([[[  2.,   3.],
        [  6.,   7.]],
       [[ 10.,  11.],
        [ 14.,  15.]]])]
>>> mt.dsplit(x, mt.array([3, 6])).execute()
[array([[[  0.,   1.,   2.],
        [  4.,   5.,   6.]],
       [[  8.,   9.,  10.],
        [ 12.,  13.,  14.]]]),
 array([[[  3.],
        [  7.]],
       [[ 11.],
        [ 15.]]]),
 array([], dtype=float64)]
```
