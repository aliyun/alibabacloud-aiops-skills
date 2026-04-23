# maxframe.tensor.linalg.cholesky

### maxframe.tensor.linalg.cholesky(a, lower=False)

Cholesky decomposition.

Return the Cholesky decomposition, L \* L.H, of the square matrix a,
where L is lower-triangular and .H is the conjugate transpose operator
(which is the ordinary transpose if a is real-valued).  a must be
Hermitian (symmetric if real-valued) and positive-definite.  Only L is
actually returned.

* **Parameters:**
  * **a** ( *(* *...* *,* *M* *,* *M* *)* *array_like*) – Hermitian (symmetric if all elements are real), positive-definite
    input matrix.
  * **lower** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – Whether to compute the upper or lower triangular Cholesky
    factorization.  Default is upper-triangular.
* **Returns:**
  **L** – Upper or lower-triangular Cholesky factor of a.
* **Return type:**
  (…, M, M) array_like
* **Raises:**
  **LinAlgError** – If the decomposition fails, for example, if a is not
      positive-definite.

### Notes

Broadcasting rules apply, see the mt.linalg documentation for
details.

The Cholesky decomposition is often used as a fast way of solving

$$
A \mathbf{x} = \mathbf{b}

$$

(when A is both Hermitian/symmetric and positive-definite).

First, we solve for $\mathbf{y}$ in

$$
L \mathbf{y} = \mathbf{b},

$$

and then for $\mathbf{x}$ in

$$
L.H \mathbf{x} = \mathbf{y}.

$$

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> A = mt.array([[1,-2j],[2j,5]])
>>> A.execute()
array([[ 1.+0.j,  0.-2.j],
       [ 0.+2.j,  5.+0.j]])
>>> L = mt.linalg.cholesky(A, lower=True)
>>> L.execute()
array([[ 1.+0.j,  0.+0.j],
       [ 0.+2.j,  1.+0.j]])
>>> mt.dot(L, L.T.conj()).execute() # verify that L * L.H = A
array([[ 1.+0.j,  0.-2.j],
       [ 0.+2.j,  5.+0.j]])
>>> A = [[1,-2j],[2j,5]] # what happens if A is only array_like?
>>> mt.linalg.cholesky(A, lower=True).execute()
array([[ 1.+0.j,  0.+0.j],
       [ 0.+2.j,  1.+0.j]])
```
