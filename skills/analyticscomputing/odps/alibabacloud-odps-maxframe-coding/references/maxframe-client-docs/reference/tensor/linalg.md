# Linear Algebra

## Matrix and vector products

| [`maxframe.tensor.dot`](generated/maxframe.tensor.dot.md#maxframe.tensor.dot)                   | Dot product of two arrays.                                               |
|-------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| [`maxframe.tensor.vdot`](generated/maxframe.tensor.vdot.md#maxframe.tensor.vdot)                | Return the dot product of two vectors.                                   |
| [`maxframe.tensor.inner`](generated/maxframe.tensor.inner.md#maxframe.tensor.inner)             | Returns the inner product of a and b for arrays of floating point types. |
| [`maxframe.tensor.matmul`](generated/maxframe.tensor.matmul.md#maxframe.tensor.matmul)          | Matrix product of two tensors.                                           |
| [`maxframe.tensor.tensordot`](generated/maxframe.tensor.tensordot.md#maxframe.tensor.tensordot) | Compute tensor dot product along specified axes for tensors >= 1-D.      |
| [`maxframe.tensor.einsum`](generated/maxframe.tensor.einsum.md#maxframe.tensor.einsum)          | Evaluates the Einstein summation convention on the operands.             |

## Decompositions

| [`maxframe.tensor.linalg.cholesky`](generated/maxframe.tensor.linalg.cholesky.md#maxframe.tensor.linalg.cholesky)   | Cholesky decomposition.                   |
|---------------------------------------------------------------------------------------------------------------------|-------------------------------------------|
| [`maxframe.tensor.linalg.lu`](generated/maxframe.tensor.linalg.lu.md#maxframe.tensor.linalg.lu)                     | LU decomposition                          |
| [`maxframe.tensor.linalg.qr`](generated/maxframe.tensor.linalg.qr.md#maxframe.tensor.linalg.qr)                     | Compute the qr factorization of a matrix. |
| [`maxframe.tensor.linalg.svd`](generated/maxframe.tensor.linalg.svd.md#maxframe.tensor.linalg.svd)                  | Singular Value Decomposition.             |

## Norms and other numbers

| [`maxframe.tensor.linalg.matrix_norm`](generated/maxframe.tensor.linalg.matrix_norm.md#maxframe.tensor.linalg.matrix_norm)   | Computes the matrix norm of a matrix (or a stack of matrices) `x`.   |
|------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [`maxframe.tensor.linalg.norm`](generated/maxframe.tensor.linalg.norm.md#maxframe.tensor.linalg.norm)                        | Matrix or vector norm.                                               |
| [`maxframe.tensor.linalg.vector_norm`](generated/maxframe.tensor.linalg.vector_norm.md#maxframe.tensor.linalg.vector_norm)   | Computes the vector norm of a vector (or batch of vectors) `x`.      |

## Solving equations and inverting matrices

| [`maxframe.tensor.linalg.inv`](generated/maxframe.tensor.linalg.inv.md#maxframe.tensor.linalg.inv)                                        | Compute the (multiplicative) inverse of a matrix.                    |
|-------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [`maxframe.tensor.linalg.lstsq`](generated/maxframe.tensor.linalg.lstsq.md#maxframe.tensor.linalg.lstsq)                                  | Return the least-squares solution to a linear matrix equation.       |
| [`maxframe.tensor.linalg.solve`](generated/maxframe.tensor.linalg.solve.md#maxframe.tensor.linalg.solve)                                  | Solve the equation `a x = b` for `x`.                                |
| [`maxframe.tensor.linalg.solve_triangular`](generated/maxframe.tensor.linalg.solve_triangular.md#maxframe.tensor.linalg.solve_triangular) | Solve the equation a x = b for x, assuming a is a triangular matrix. |
