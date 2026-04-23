# maxframe.tensor.linalg.lu

### maxframe.tensor.linalg.lu(a)

LU decomposition

The decomposition is::
: A = P L U

where P is a permutation matrix, L lower triangular with unit diagonal elements,
and U upper triangular.

* **Parameters:**
  **a** ( *(**M* *,* *N* *)* *array_like*) – Array to decompose
* **Returns:**
  * **p** ( *(M, M) ndarray*) – Permutation matrix
  * **l** ( *(M, K) ndarray*) – Lower triangular or trapezoidal matrix with unit diagonal.
    K = min(M, N)
  * **u** ( *(K, N) ndarray*) – Upper triangular or trapezoidal matrix

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> A = mt.array([[1,2],[2,3]])
>>> A.execute()
array([[ 1,  2],
       [ 2,  3]])
>>> P, L, U = mt.linalg.lu(A)
>>> P.execute()
array([[ 0,  1],
       [ 1,  0]])
>>> L.execute()
array([[ 1,  0],
       [ 0.5,  1]])
>>> U.execute()
array([[ 2,  3],
       [ 0,  0.5]])
>>> mt.dot(P.dot(L), U).execute() # verify that PL * U = A
array([[ 1,  2],
       [ 2,  3]])
```
