# maxframe.tensor.array_split

### maxframe.tensor.array_split(a, indices_or_sections, axis=0)

Split a tensor into multiple sub-tensors.

Please refer to the `split` documentation.  The only difference
between these functions is that `array_split` allows
indices_or_sections to be an integer that does *not* equally
divide the axis. For a tensor of length l that should be split
into n sections, it returns l % n sub-arrays of size l//n + 1
and the rest of size l//n.

#### SEE ALSO
[`split`](maxframe.tensor.split.md#maxframe.tensor.split)
: Split tensor into multiple sub-tensors of equal size.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.arange(8.0)
>>> mt.array_split(x, 3).execute()
    [array([ 0.,  1.,  2.]), array([ 3.,  4.,  5.]), array([ 6.,  7.])]
```

```pycon
>>> x = mt.arange(7.0)
>>> mt.array_split(x, 3).execute()
    [array([ 0.,  1.,  2.]), array([ 3.,  4.]), array([ 5.,  6.])]
```
