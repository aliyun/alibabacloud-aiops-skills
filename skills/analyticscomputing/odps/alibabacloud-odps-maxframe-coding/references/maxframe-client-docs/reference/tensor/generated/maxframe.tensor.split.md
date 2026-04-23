# maxframe.tensor.split

### maxframe.tensor.split(ary, indices_or_sections, axis=0)

Split a tensor into multiple sub-tensors.

* **Parameters:**
  * **ary** (*Tensor*) – Tensor to be divided into sub-tensors.
  * **indices_or_sections** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *1-D tensor*) – 

    If indices_or_sections is an integer, N, the array will be divided
    into N equal tensors along axis.  If such a split is not possible,
    an error is raised.

    If indices_or_sections is a 1-D tensor of sorted integers, the entries
    indicate where along axis the array is split.  For example,
    `[2, 3]` would, for `axis=0`, result in
    > - ary[:2]
    > - ary[2:3]
    > - ary[3:]

    If an index exceeds the dimension of the tensor along axis,
    an empty sub-tensor is returned correspondingly.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The axis along which to split, default is 0.
* **Returns:**
  **sub-tensors** – A list of sub-tensors.
* **Return type:**
  [list](https://docs.python.org/3/library/stdtypes.html#list) of Tensors
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If indices_or_sections is given as an integer, but
      a split does not result in equal division.

#### SEE ALSO
[`array_split`](maxframe.tensor.array_split.md#maxframe.tensor.array_split)
: Split a tensor into multiple sub-tensors of equal or near-equal size.  Does not raise an exception if an equal division cannot be made.

[`hsplit`](maxframe.tensor.hsplit.md#maxframe.tensor.hsplit)
: Split  into multiple sub-arrays horizontally (column-wise).

[`vsplit`](maxframe.tensor.vsplit.md#maxframe.tensor.vsplit)
: Split tensor into multiple sub-tensors vertically (row wise).

[`dsplit`](maxframe.tensor.dsplit.md#maxframe.tensor.dsplit)
: Split tensor into multiple sub-tensors along the 3rd axis (depth).

[`concatenate`](maxframe.tensor.concatenate.md#maxframe.tensor.concatenate)
: Join a sequence of tensors along an existing axis.

`stack`
: Join a sequence of tensors along a new axis.

`hstack`
: Stack tensors in sequence horizontally (column wise).

[`vstack`](maxframe.tensor.vstack.md#maxframe.tensor.vstack)
: Stack tensors in sequence vertically (row wise).

`dstack`
: Stack tensors in sequence depth wise (along third dimension).

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.arange(9.0)
>>> mt.split(x, 3).execute()
[array([ 0.,  1.,  2.]), array([ 3.,  4.,  5.]), array([ 6.,  7.,  8.])]
```

```pycon
>>> x = mt.arange(8.0)
>>> mt.split(x, [3, 5, 6, 10]).execute()
[array([ 0.,  1.,  2.]),
 array([ 3.,  4.]),
 array([ 5.]),
 array([ 6.,  7.]),
 array([], dtype=float64)]
```
