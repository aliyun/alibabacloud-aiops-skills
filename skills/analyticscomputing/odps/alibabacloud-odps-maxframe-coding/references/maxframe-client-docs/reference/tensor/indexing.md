<a id="tensor-indexing"></a>

# Tensor Indexing Routines

## Generating index arrays

| [`maxframe.tensor.c_`](generated/maxframe.tensor.c_.md#maxframe.tensor.c_)                                  | Translates slice objects to concatenation along the second axis.                    |
|-------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| [`maxframe.tensor.r_`](generated/maxframe.tensor.r_.md#maxframe.tensor.r_)                                  | Translates slice objects to concatenation along the first axis.                     |
| [`maxframe.tensor.nonzero`](generated/maxframe.tensor.nonzero.md#maxframe.tensor.nonzero)                   | Return the indices of the elements that are non-zero.                               |
| [`maxframe.tensor.where`](generated/maxframe.tensor.where.md#maxframe.tensor.where)                         | Return elements, either from x or y, depending on condition.                        |
| [`maxframe.tensor.indices`](generated/maxframe.tensor.indices.md#maxframe.tensor.indices)                   | Return a tensor representing the indices of a grid.                                 |
| [`maxframe.tensor.ogrid`](generated/maxframe.tensor.ogrid.md#maxframe.tensor.ogrid)                         | Construct a multi-dimensional "meshgrid".                                           |
| [`maxframe.tensor.unravel_index`](generated/maxframe.tensor.unravel_index.md#maxframe.tensor.unravel_index) | Converts a flat index or tensor of flat indices into a tuple of coordinate tensors. |

## Indexing-like operations

| [`maxframe.tensor.take`](generated/maxframe.tensor.take.md#maxframe.tensor.take)             | Take elements from a tensor along an axis.                                   |
|----------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`maxframe.tensor.choose`](generated/maxframe.tensor.choose.md#maxframe.tensor.choose)       | Construct a tensor from an index tensor and a set of tensors to choose from. |
| [`maxframe.tensor.compress`](generated/maxframe.tensor.compress.md#maxframe.tensor.compress) | Return selected slices of a tensor along given axis.                         |
| [`maxframe.tensor.diag`](generated/maxframe.tensor.diag.md#maxframe.tensor.diag)             | Extract a diagonal or construct a diagonal tensor.                           |

## Inserting data into arrays

| [`maxframe.tensor.fill_diagonal`](generated/maxframe.tensor.fill_diagonal.md#maxframe.tensor.fill_diagonal)   | Fill the main diagonal of the given tensor of any dimensionality.   |
|---------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
