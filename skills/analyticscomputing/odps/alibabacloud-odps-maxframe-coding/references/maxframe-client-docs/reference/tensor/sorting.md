# Sorting, Searching, and Counting

## Sorting

| [`maxframe.tensor.sort`](generated/maxframe.tensor.sort.md#maxframe.tensor.sort)                         | Return a sorted copy of a tensor.                                                                     |
|----------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| [`maxframe.tensor.argsort`](generated/maxframe.tensor.argsort.md#maxframe.tensor.argsort)                | Returns the indices that would sort a tensor.                                                         |
| [`maxframe.tensor.partition`](generated/maxframe.tensor.partition.md#maxframe.tensor.partition)          | Return a partitioned copy of a tensor.                                                                |
| [`maxframe.tensor.argpartition`](generated/maxframe.tensor.argpartition.md#maxframe.tensor.argpartition) | Perform an indirect partition along the given axis using the algorithm specified by the kind keyword. |

## Searching

| [`maxframe.tensor.argmax`](generated/maxframe.tensor.argmax.md#maxframe.tensor.argmax)                | Returns the indices of the maximum values along an axis.                      |
|-------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`maxframe.tensor.nanargmax`](generated/maxframe.tensor.nanargmax.md#maxframe.tensor.nanargmax)       | Return the indices of the maximum values in the specified axis ignoring NaNs. |
| [`maxframe.tensor.argmin`](generated/maxframe.tensor.argmin.md#maxframe.tensor.argmin)                | Returns the indices of the minimum values along an axis.                      |
| [`maxframe.tensor.nanargmin`](generated/maxframe.tensor.nanargmin.md#maxframe.tensor.nanargmin)       | Return the indices of the minimum values in the specified axis ignoring NaNs. |
| [`maxframe.tensor.nonzero`](generated/maxframe.tensor.nonzero.md#maxframe.tensor.nonzero)             | Return the indices of the elements that are non-zero.                         |
| [`maxframe.tensor.flatnonzero`](generated/maxframe.tensor.flatnonzero.md#maxframe.tensor.flatnonzero) | Return indices that are non-zero in the flattened version of a.               |

## Counting

| [`maxframe.tensor.argwhere`](generated/maxframe.tensor.argwhere.md#maxframe.tensor.argwhere)                | Find the indices of tensor elements that are non-zero, grouped by element.   |
|-------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`maxframe.tensor.count_nonzero`](generated/maxframe.tensor.count_nonzero.md#maxframe.tensor.count_nonzero) | Counts the number of non-zero values in the tensor `a`.                      |
