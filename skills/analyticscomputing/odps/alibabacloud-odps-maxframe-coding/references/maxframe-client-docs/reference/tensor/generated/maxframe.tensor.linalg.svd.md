# maxframe.tensor.linalg.svd

### maxframe.tensor.linalg.svd(a, method='tsqr')

Singular Value Decomposition.

When a is a 2D tensor, it is factorized as `u @ np.diag(s) @ vh
= (u * s) @ vh`, where u and vh are 2D unitary tensors and s is a 1D
tensor of a’s singular values. When a is higher-dimensional, SVD is
applied in stacked mode as explained below.

* **Parameters:**
  * **a** ( *(* *...* *,* *M* *,* *N* *)* *array_like*) – A real or complex tensor with `a.ndim >= 2`.
  * **method** ( *{'tsqr'}* *,* *optional*) – 

    method to calculate qr factorization, tsqr as default

    TSQR is presented in:
    > A. Benson, D. Gleich, and J. Demmel.
    > Direct QR factorizations for tall-and-skinny matrices in
    > MapReduce architectures.
    > IEEE International Conference on Big Data, 2013.
    > [http://arxiv.org/abs/1301.1071](http://arxiv.org/abs/1301.1071)
* **Returns:**
  * **u** ( *{ (…, M, M), (…, M, K) } tensor*) – Unitary tensor(s). The first `a.ndim - 2` dimensions have the same
    size as those of the input a. The size of the last two dimensions
    depends on the value of full_matrices. Only returned when
    compute_uv is True.
  * **s** ( *(…, K) tensor*) – Vector(s) with the singular values, within each vector sorted in
    descending order. The first `a.ndim - 2` dimensions have the same
    size as those of the input a.
  * **vh** ( *{ (…, N, N), (…, K, N) } tensor*) – Unitary tensor(s). The first `a.ndim - 2` dimensions have the same
    size as those of the input a. The size of the last two dimensions
    depends on the value of full_matrices. Only returned when
    compute_uv is True.
* **Raises:**
  **LinAlgError** – If SVD computation does not converge.

### Notes

SVD is usually described for the factorization of a 2D matrix $A$.
The higher-dimensional case will be discussed below. In the 2D case, SVD is
written as $A = U S V^H$, where $A = a$, $U= u$,
$S= \mathtt{np.diag}(s)$ and $V^H = vh$. The 1D tensor s
contains the singular values of a and u and vh are unitary. The rows
of vh are the eigenvectors of $A^H A$ and the columns of u are
the eigenvectors of $A A^H$. In both cases the corresponding
(possibly non-zero) eigenvalues are given by `s**2`.

If a has more than two dimensions, then broadcasting rules apply, as
explained in [Linear algebra on several matrices at once](https://numpy.org/doc/stable/reference/routines.linalg.html#routines-linalg-broadcasting). This means that SVD is
working in “stacked” mode: it iterates over all indices of the first
`a.ndim - 2` dimensions and for each combination SVD is applied to the
last two indices. The matrix a can be reconstructed from the
decomposition with either `(u * s[..., None, :]) @ vh` or
`u @ (s[..., None] * vh)`. (The `@` operator can be replaced by the
function `mt.matmul` for python versions below 3.5.)

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> a = mt.random.randn(9, 6) + 1j*mt.random.randn(9, 6)
>>> b = mt.random.randn(2, 7, 8, 3) + 1j*mt.random.randn(2, 7, 8, 3)
```

Reconstruction based on reduced SVD, 2D case:

```pycon
>>> u, s, vh = mt.linalg.svd(a)
>>> u.shape, s.shape, vh.shape
((9, 6), (6,), (6, 6))
>>> np.allclose(a, np.dot(u * s, vh))
True
>>> smat = np.diag(s)
>>> np.allclose(a, np.dot(u, np.dot(smat, vh)))
True
```
