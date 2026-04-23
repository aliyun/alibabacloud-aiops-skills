# maxframe.tensor.linalg.inv

### maxframe.tensor.linalg.inv(a, sparse=None)

Compute the (multiplicative) inverse of a matrix.
Given a square matrix a, return the matrix ainv satisfying
`dot(a, ainv) = dot(ainv, a) = eye(a.shape[0])`.

* **Parameters:**
  * **a** ( *(* *...* *,* *M* *,* *M* *)* *array_like*) – Matrix to be inverted.
  * **sparse** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Return sparse value or not.
* **Returns:**
  **ainv** – (Multiplicative) inverse of the matrix a.
* **Return type:**
  (…, M, M) ndarray or matrix
* **Raises:**
  **LinAlgError** – If a is not square or inversion fails.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> a = np.array([[1., 2.], [3., 4.]])
>>> ainv = mt.linalg.inv(a)
>>> mt.allclose(mt.dot(a, ainv), mt.eye(2)).execute()
True
```

```pycon
>>> mt.allclose(mt.dot(ainv, a), mt.eye(2)).execute()
True
```

```pycon
>>> ainv.execute()
array([[ -2. ,  1. ],
       [ 1.5, -0.5]])
```
