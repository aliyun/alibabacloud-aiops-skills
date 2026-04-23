# maxframe.tensor.c_

### maxframe.tensor.c_ *= <maxframe.tensor.lib.index_tricks.CClass object>*

Translates slice objects to concatenation along the second axis.

This is short-hand for `mt.r_['-1,2,0', index expression]`, which is
useful because of its common occurrence. In particular, tensors will be
stacked along their last axis after being upgraded to at least 2-D with
1’s post-pended to the shape (column vectors made out of 1-D tensors).

#### SEE ALSO
`column_stack`
: Stack 1-D tensors as columns into a 2-D tensor.

[`r_`](maxframe.tensor.r_.md#maxframe.tensor.r_)
: For more detailed documentation.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.c_[mt.array([1,2,3]), mt.array([4,5,6])].execute()
array([[1, 4],
       [2, 5],
       [3, 6]])
>>> mt.c_[mt.array([[1,2,3]]), 0, 0, mt.array([[4,5,6]])].execute()
array([[1, 2, 3, ..., 4, 5, 6]])
```
