# maxframe.tensor.triu

### maxframe.tensor.triu(m, k=0, gpu=None)

Upper triangle of a tensor.

Return a copy of a matrix with the elements below the k-th diagonal
zeroed.

Please refer to the documentation for tril for further details.

#### SEE ALSO
[`tril`](maxframe.tensor.tril.md#maxframe.tensor.tril)
: lower triangle of a tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.triu([[1,2,3],[4,5,6],[7,8,9],[10,11,12]], -1).execute()
array([[ 1,  2,  3],
       [ 4,  5,  6],
       [ 0,  8,  9],
       [ 0,  0, 12]])
```
