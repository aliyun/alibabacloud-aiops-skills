# Tensor Manipulation Routines

## Basic operations

| [`maxframe.tensor.copyto`](generated/maxframe.tensor.copyto.md#maxframe.tensor.copyto)   | Copies values from one array to another, broadcasting as necessary.   |
|------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| [`maxframe.tensor.ndim`](generated/maxframe.tensor.ndim.md#maxframe.tensor.ndim)         | Return the number of dimensions of a tensor.                          |
| [`maxframe.tensor.shape`](generated/maxframe.tensor.shape.md#maxframe.tensor.shape)      | Return the shape of a tensor.                                         |

## Changing array shape

| [`maxframe.tensor.reshape`](generated/maxframe.tensor.reshape.md#maxframe.tensor.reshape)                                     | Gives a new shape to a tensor without changing its data.   |
|-------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| [`maxframe.tensor.ravel`](generated/maxframe.tensor.ravel.md#maxframe.tensor.ravel)                                           | Return a contiguous flattened tensor.                      |
| [`maxframe.tensor.core.Tensor.flatten`](generated/maxframe.tensor.core.Tensor.flatten.md#maxframe.tensor.core.Tensor.flatten) | Return a copy of the tensor collapsed into one dimension.  |

## Transpose-like operations

| [`maxframe.tensor.moveaxis`](generated/maxframe.tensor.moveaxis.md#maxframe.tensor.moveaxis)                | Move axes of a tensor to new positions.                                  |
|-------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| [`maxframe.tensor.rollaxis`](generated/maxframe.tensor.rollaxis.md#maxframe.tensor.rollaxis)                | Roll the specified axis backwards, until it lies in a given position.    |
| [`maxframe.tensor.swapaxes`](generated/maxframe.tensor.swapaxes.md#maxframe.tensor.swapaxes)                | Interchange two axes of a tensor.                                        |
| [`maxframe.tensor.core.Tensor.T`](generated/maxframe.tensor.core.Tensor.T.md#maxframe.tensor.core.Tensor.T) | Same as self.transpose(), except that self is returned if self.ndim < 2. |
| [`maxframe.tensor.transpose`](generated/maxframe.tensor.transpose.md#maxframe.tensor.transpose)             | Returns an array with axes transposed.                                   |

## Changing number of dimensions

| [`maxframe.tensor.atleast_1d`](generated/maxframe.tensor.atleast_1d.md#maxframe.tensor.atleast_1d)                   | Convert inputs to tensors with at least one dimension.        |
|----------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| [`maxframe.tensor.atleast_2d`](generated/maxframe.tensor.atleast_2d.md#maxframe.tensor.atleast_2d)                   | View inputs as tensors with at least two dimensions.          |
| [`maxframe.tensor.atleast_3d`](generated/maxframe.tensor.atleast_3d.md#maxframe.tensor.atleast_3d)                   | View inputs as tensors with at least three dimensions.        |
| [`maxframe.tensor.broadcast_to`](generated/maxframe.tensor.broadcast_to.md#maxframe.tensor.broadcast_to)             | Broadcast a tensor to a new shape.                            |
| [`maxframe.tensor.broadcast_arrays`](generated/maxframe.tensor.broadcast_arrays.md#maxframe.tensor.broadcast_arrays) | Broadcast any number of arrays against each other.            |
| [`maxframe.tensor.expand_dims`](generated/maxframe.tensor.expand_dims.md#maxframe.tensor.expand_dims)                | Expand the shape of a tensor.                                 |
| [`maxframe.tensor.squeeze`](generated/maxframe.tensor.squeeze.md#maxframe.tensor.squeeze)                            | Remove single-dimensional entries from the shape of a tensor. |

## Joining tensors

| [`maxframe.tensor.concatenate`](generated/maxframe.tensor.concatenate.md#maxframe.tensor.concatenate)   | Join a sequence of arrays along an existing axis.   |
|---------------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| [`maxframe.tensor.vstack`](generated/maxframe.tensor.vstack.md#maxframe.tensor.vstack)                  | Stack tensors in sequence vertically (row wise).    |

## Splitting arrays

| [`maxframe.tensor.split`](generated/maxframe.tensor.split.md#maxframe.tensor.split)                   | Split a tensor into multiple sub-tensors.                            |
|-------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [`maxframe.tensor.array_split`](generated/maxframe.tensor.array_split.md#maxframe.tensor.array_split) | Split a tensor into multiple sub-tensors.                            |
| [`maxframe.tensor.dsplit`](generated/maxframe.tensor.dsplit.md#maxframe.tensor.dsplit)                | Split tensor into multiple sub-tensors along the 3rd axis (depth).   |
| [`maxframe.tensor.hsplit`](generated/maxframe.tensor.hsplit.md#maxframe.tensor.hsplit)                | Split a tensor into multiple sub-tensors horizontally (column-wise). |
| [`maxframe.tensor.vsplit`](generated/maxframe.tensor.vsplit.md#maxframe.tensor.vsplit)                | Split a tensor into multiple sub-tensors vertically (row-wise).      |

## Tiling arrays

| [`maxframe.tensor.tile`](generated/maxframe.tensor.tile.md#maxframe.tensor.tile)       | Construct a tensor by repeating A the number of times given by reps.   |
|----------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| [`maxframe.tensor.repeat`](generated/maxframe.tensor.repeat.md#maxframe.tensor.repeat) | Repeat elements of a tensor.                                           |

## Adding and removing elements

| [`maxframe.tensor.delete`](generated/maxframe.tensor.delete.md#maxframe.tensor.delete)   | Return a new array with sub-arrays along an axis deleted.    |
|------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| [`maxframe.tensor.insert`](generated/maxframe.tensor.insert.md#maxframe.tensor.insert)   | Insert values along the given axis before the given indices. |

## Rearranging elements

| [`maxframe.tensor.flip`](generated/maxframe.tensor.flip.md#maxframe.tensor.flip)       | Reverse the order of elements in a tensor along the given axis.   |
|----------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| [`maxframe.tensor.fliplr`](generated/maxframe.tensor.fliplr.md#maxframe.tensor.fliplr) | Flip tensor in the left/right direction.                          |
| [`maxframe.tensor.flipud`](generated/maxframe.tensor.flipud.md#maxframe.tensor.flipud) | Flip tensor in the up/down direction.                             |
| [`maxframe.tensor.roll`](generated/maxframe.tensor.roll.md#maxframe.tensor.roll)       | Roll tensor elements along a given axis.                          |
