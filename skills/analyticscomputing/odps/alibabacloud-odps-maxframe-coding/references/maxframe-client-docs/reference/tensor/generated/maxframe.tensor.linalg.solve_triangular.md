# maxframe.tensor.linalg.solve_triangular

### maxframe.tensor.linalg.solve_triangular(a, b, lower=False, sparse=None)

Solve the equation a x = b for x, assuming a is a triangular matrix.

* **Parameters:**
  * **a** ( *(**M* *,* *M* *)* *array_like*) – A triangular matrix
  * **b** ( *(**M* *,* *) or*  *(**M* *,* *N* *)* *array_like*) – Right-hand side matrix in a x = b
  * **lower** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Use only data contained in the lower triangle of a.
    Default is to use upper triangle.
  * **sparse** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Return sparse value or not.
* **Returns:**
  **x** – Solution to the system a x = b.  Shape of return matches b.
* **Return type:**
  (M,) or (M, N) ndarray

### Examples

Solve the lower triangular system a x = b, where::
: > [3  0  0  0]       [4]
  <br/>
  a =  [2  1  0  0]   b = [2]
  : [1  0  1  0]       [4]
    [1  1  1  1]       [2]

```pycon
>>> import maxframe.tensor as mt
>>> a = mt.array([[3, 0, 0, 0], [2, 1, 0, 0], [1, 0, 1, 0], [1, 1, 1, 1]])
>>> b = mt.array([4, 2, 4, 2])
>>> x = mt.linalg.solve_triangular(a, b, lower=True)
>>> x.execute()
array([ 1.33333333, -0.66666667,  2.66666667, -1.33333333])
```

```pycon
>>> a.dot(x).execute()  # Check the result
array([ 4.,  2.,  4.,  2.])
```
