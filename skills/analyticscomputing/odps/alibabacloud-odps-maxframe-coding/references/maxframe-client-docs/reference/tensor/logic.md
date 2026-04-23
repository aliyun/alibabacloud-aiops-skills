# Logic Functions

## Truth value testing

| [`maxframe.tensor.all`](generated/maxframe.tensor.all.md#maxframe.tensor.all)   | Test whether all array elements along a given axis evaluate to True.   |
|---------------------------------------------------------------------------------|------------------------------------------------------------------------|
| [`maxframe.tensor.any`](generated/maxframe.tensor.any.md#maxframe.tensor.any)   | Test whether any tensor element along a given axis evaluates to True.  |

## Array contents

| [`maxframe.tensor.isfinite`](generated/maxframe.tensor.isfinite.md#maxframe.tensor.isfinite)   | Test element-wise for finiteness (not infinity or not Not a Number).   |
|------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| [`maxframe.tensor.isinf`](generated/maxframe.tensor.isinf.md#maxframe.tensor.isinf)            | Test element-wise for positive or negative infinity.                   |
| [`maxframe.tensor.isnan`](generated/maxframe.tensor.isnan.md#maxframe.tensor.isnan)            | Test element-wise for NaN and return result as a boolean tensor.       |

## Array type testing

| [`maxframe.tensor.iscomplex`](generated/maxframe.tensor.iscomplex.md#maxframe.tensor.iscomplex)   | Returns a bool tensor, where True if input element is complex.   |
|---------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| [`maxframe.tensor.isreal`](generated/maxframe.tensor.isreal.md#maxframe.tensor.isreal)            | Returns a bool tensor, where True if input element is real.      |

## Logic operations

| [`maxframe.tensor.logical_and`](generated/maxframe.tensor.logical_and.md#maxframe.tensor.logical_and)   | Compute the truth value of x1 AND x2 element-wise.   |
|---------------------------------------------------------------------------------------------------------|------------------------------------------------------|
| [`maxframe.tensor.logical_or`](generated/maxframe.tensor.logical_or.md#maxframe.tensor.logical_or)      | Compute the truth value of x1 OR x2 element-wise.    |
| [`maxframe.tensor.logical_not`](generated/maxframe.tensor.logical_not.md#maxframe.tensor.logical_not)   | Compute the truth value of NOT x element-wise.       |
| [`maxframe.tensor.logical_xor`](generated/maxframe.tensor.logical_xor.md#maxframe.tensor.logical_xor)   | Compute the truth value of x1 XOR x2, element-wise.  |

## Comparison

| [`maxframe.tensor.allclose`](generated/maxframe.tensor.allclose.md#maxframe.tensor.allclose)                | Returns True if two tensors are element-wise equal within a tolerance.                |
|-------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| [`maxframe.tensor.isclose`](generated/maxframe.tensor.isclose.md#maxframe.tensor.isclose)                   | Returns a boolean tensor where two tensors are element-wise equal within a tolerance. |
| [`maxframe.tensor.array_equal`](generated/maxframe.tensor.array_equal.md#maxframe.tensor.array_equal)       | True if two tensors have the same shape and elements, False otherwise.                |
| [`maxframe.tensor.greater`](generated/maxframe.tensor.greater.md#maxframe.tensor.greater)                   | Return the truth value of (x1 > x2) element-wise.                                     |
| [`maxframe.tensor.greater_equal`](generated/maxframe.tensor.greater_equal.md#maxframe.tensor.greater_equal) | Return the truth value of (x1 >= x2) element-wise.                                    |
| [`maxframe.tensor.less`](generated/maxframe.tensor.less.md#maxframe.tensor.less)                            | Return the truth value of (x1 < x2) element-wise.                                     |
| [`maxframe.tensor.less_equal`](generated/maxframe.tensor.less_equal.md#maxframe.tensor.less_equal)          | Return the truth value of (x1 =< x2) element-wise.                                    |
| [`maxframe.tensor.equal`](generated/maxframe.tensor.equal.md#maxframe.tensor.equal)                         | Return (x1 == x2) element-wise.                                                       |
| [`maxframe.tensor.not_equal`](generated/maxframe.tensor.not_equal.md#maxframe.tensor.not_equal)             | Return (x1 != x2) element-wise.                                                       |
