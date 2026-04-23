# maxframe.tensor.linalg.solve

### maxframe.tensor.linalg.solve(a, b, sym_pos=False, sparse=None)

Solve the equation `a x = b` for `x`.

* **Parameters:**
  * **a** ( *(**M* *,* *M* *)* *array_like*) – A square matrix.
  * **b** ( *(**M* *,* *) or*  *(**M* *,* *N* *)* *array_like*) – Right-hand side matrix in `a x = b`.
  * **sym_pos** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – Assume a is symmetric and positive definite. If `True`, use Cholesky
    decomposition.
  * **sparse** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Return sparse value or not.
* **Returns:**
  * **x** ( *(M,) or (M, N) ndarray*)
  * Solution to the system `a x = b`.  Shape of the return matches the
  * shape of b.
* **Raises:**
  * **LinAlgError** – 
  * **If a is singular.** – 

### Examples

Given a and b, solve for x:

```pycon
>>> import maxframe.tensor as mt
>>> a = mt.array([[3, 2, 0], [1, -1, 0], [0, 5, 1]])
>>> b = mt.array([2, 4, -1])
>>> x = mt.linalg.solve(a, b)
>>> x.execute()
array([ 2., -2.,  9.])
```

```pycon
>>> mt.dot(a, x).execute()  # Check the result
array([ 2., 4., -1.])
```
