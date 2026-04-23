# maxframe.learn.metrics.pairwise.manhattan_distances

### maxframe.learn.metrics.pairwise.manhattan_distances(X, Y=None)

Compute the L1 distances between the vectors in X and Y.

Read more in the User Guide.

* **Parameters:**
  * **X** (*array_like*) – A tensor with shape (n_samples_X, n_features).
  * **Y** (*array_like* *,* *optional*) – A tensor with shape (n_samples_Y, n_features).
* **Returns:**
  **D** – Shape is (n_samples_X, n_samples_Y) and D contains
  the pairwise L1 distances.
* **Return type:**
  Tensor

### Examples

```pycon
>>> from maxframe.learn.metrics.pairwise import manhattan_distances
>>> manhattan_distances([[3]], [[3]]).execute()
array([[0.]])
>>> manhattan_distances([[3]], [[2]]).execute()
array([[1.]])
>>> manhattan_distances([[2]], [[3]]).execute()
array([[1.]])
>>> manhattan_distances([[1, 2], [3, 4]],         [[1, 2], [0, 3]]).execute()
array([[0., 2.],
       [4., 4.]])
```
