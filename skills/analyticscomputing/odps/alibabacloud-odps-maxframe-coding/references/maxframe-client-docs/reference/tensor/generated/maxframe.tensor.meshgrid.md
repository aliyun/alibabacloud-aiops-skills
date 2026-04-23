# maxframe.tensor.meshgrid

### maxframe.tensor.meshgrid(\*xi, \*\*kwargs)

Return coordinate matrices from coordinate vectors.

Make N-D coordinate arrays for vectorized evaluations of
N-D scalar/vector fields over N-D grids, given
one-dimensional coordinate tensors x1, x2,…, xn.

* **Parameters:**
  * **x1** (*array_like*) – 1-D arrays representing the coordinates of a grid.
  * **x2** (*array_like*) – 1-D arrays representing the coordinates of a grid.
  * **...** (*array_like*) – 1-D arrays representing the coordinates of a grid.
  * **xn** (*array_like*) – 1-D arrays representing the coordinates of a grid.
  * **indexing** ( *{'xy'* *,*  *'ij'}* *,* *optional*) – Cartesian (‘xy’, default) or matrix (‘ij’) indexing of output.
    See Notes for more details.
  * **sparse** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If True a sparse grid is returned in order to conserve memory.
    Default is False.
* **Returns:**
  **X1, X2,…, XN** – For vectors x1, x2,…, ‘xn’ with lengths `Ni=len(xi)` ,
  return `(N1, N2, N3,...Nn)` shaped tensors if indexing=’ij’
  or `(N2, N1, N3,...Nn)` shaped tensors if indexing=’xy’
  with the elements of xi repeated to fill the matrix along
  the first dimension for x1, the second for x2 and so on.
* **Return type:**
  Tensor

### Notes

This function supports both indexing conventions through the indexing
keyword argument.  Giving the string ‘ij’ returns a meshgrid with
matrix indexing, while ‘xy’ returns a meshgrid with Cartesian indexing.
In the 2-D case with inputs of length M and N, the outputs are of shape
(N, M) for ‘xy’ indexing and (M, N) for ‘ij’ indexing.  In the 3-D case
with inputs of length M, N and P, outputs are of shape (N, M, P) for
‘xy’ indexing and (M, N, P) for ‘ij’ indexing.  The difference is
illustrated by the following code snippet:

```default
xv, yv = mt.meshgrid(x, y, sparse=False, indexing='ij')
for i in range(nx):
    for j in range(ny):
        # treat xv[i,j], yv[i,j]

xv, yv = mt.meshgrid(x, y, sparse=False, indexing='xy')
for i in range(nx):
    for j in range(ny):
        # treat xv[j,i], yv[j,i]
```

In the 1-D and 0-D case, the indexing and sparse keywords have no effect.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> nx, ny = (3, 2)
>>> x = mt.linspace(0, 1, nx)
>>> y = mt.linspace(0, 1, ny)
>>> xv, yv = mt.meshgrid(x, y)
>>> xv.execute()
array([[ 0. ,  0.5,  1. ],
       [ 0. ,  0.5,  1. ]])
>>> yv.execute()
array([[ 0.,  0.,  0.],
       [ 1.,  1.,  1.]])
>>> xv, yv = mt.meshgrid(x, y, sparse=True)  # make sparse output arrays
>>> xv.execute()
array([[ 0. ,  0.5,  1. ]])
>>> yv.execute()
array([[ 0.],
       [ 1.]])
```

meshgrid is very useful to evaluate functions on a grid.

```pycon
>>> import matplotlib.pyplot as plt
>>> x = mt.arange(-5, 5, 0.1)
>>> y = mt.arange(-5, 5, 0.1)
>>> xx, yy = mt.meshgrid(x, y, sparse=True)
>>> z = mt.sin(xx**2 + yy**2) / (xx**2 + yy**2)
>>> h = plt.contourf(x,y,z)
```
