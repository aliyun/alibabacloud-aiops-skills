<a id="tensor-creation"></a>

# Tensor Creation Routines

## From shape or value

| [`maxframe.tensor.ones`](generated/maxframe.tensor.ones.md#maxframe.tensor.ones)                   | Return a new tensor of given shape and type, filled with ones.             |
|----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`maxframe.tensor.zeros`](generated/maxframe.tensor.zeros.md#maxframe.tensor.zeros)                | Return a new tensor of given shape and type, filled with zeros.            |
| [`maxframe.tensor.empty`](generated/maxframe.tensor.empty.md#maxframe.tensor.empty)                | Return a new tensor of given shape and type, without initializing entries. |
| [`maxframe.tensor.empty_like`](generated/maxframe.tensor.empty_like.md#maxframe.tensor.empty_like) | Return a new tensor with the same shape and type as a given tensor.        |
| [`maxframe.tensor.full`](generated/maxframe.tensor.full.md#maxframe.tensor.full)                   | Return a new tensor of given shape and type, filled with fill_value.       |
| [`maxframe.tensor.full_like`](generated/maxframe.tensor.full_like.md#maxframe.tensor.full_like)    | Return a full tensor with the same shape and type as a given tensor.       |

## From existing data

| [`maxframe.tensor.tensor`](generated/maxframe.tensor.tensor.md#maxframe.tensor.tensor)    |                                |
|-------------------------------------------------------------------------------------------|--------------------------------|
| [`maxframe.tensor.array`](generated/maxframe.tensor.array.md#maxframe.tensor.array)       | Create a tensor.               |
| [`maxframe.tensor.asarray`](generated/maxframe.tensor.asarray.md#maxframe.tensor.asarray) | Convert the input to an array. |

## Building matrices

| [`maxframe.tensor.diag`](generated/maxframe.tensor.diag.md#maxframe.tensor.diag)             | Extract a diagonal or construct a diagonal tensor.                      |
|----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`maxframe.tensor.diagflat`](generated/maxframe.tensor.diagflat.md#maxframe.tensor.diagflat) | Create a two-dimensional tensor with the flattened input as a diagonal. |
| [`maxframe.tensor.tril`](generated/maxframe.tensor.tril.md#maxframe.tensor.tril)             | Lower triangle of a tensor.                                             |
| [`maxframe.tensor.triu`](generated/maxframe.tensor.triu.md#maxframe.tensor.triu)             | Upper triangle of a tensor.                                             |

## Numerical ranges

| [`maxframe.tensor.arange`](generated/maxframe.tensor.arange.md#maxframe.tensor.arange)       | Return evenly spaced values within a given interval.    |
|----------------------------------------------------------------------------------------------|---------------------------------------------------------|
| [`maxframe.tensor.linspace`](generated/maxframe.tensor.linspace.md#maxframe.tensor.linspace) | Return evenly spaced numbers over a specified interval. |
| [`maxframe.tensor.meshgrid`](generated/maxframe.tensor.meshgrid.md#maxframe.tensor.meshgrid) | Return coordinate matrices from coordinate vectors.     |
| [`maxframe.tensor.mgrid`](generated/maxframe.tensor.mgrid.md#maxframe.tensor.mgrid)          | Construct a multi-dimensional "meshgrid".               |
| [`maxframe.tensor.ogrid`](generated/maxframe.tensor.ogrid.md#maxframe.tensor.ogrid)          | Construct a multi-dimensional "meshgrid".               |
