# maxframe.learn.metrics.pairwise.euclidean_distances

### maxframe.learn.metrics.pairwise.euclidean_distances(X, Y=None, Y_norm_squared=None, squared=False, X_norm_squared=None)

Considering the rows of X (and Y=X) as vectors, compute the
distance matrix between each pair of vectors.

For efficiency reasons, the euclidean distance between a pair of row
vector x and y is computed as:

```default
dist(x, y) = sqrt(dot(x, x) - 2 * dot(x, y) + dot(y, y))
```

This formulation has two advantages over other ways of computing distances.
First, it is computationally efficient when dealing with sparse data.
Second, if one argument varies but the other remains unchanged, then
dot(x, x) and/or dot(y, y) can be pre-computed.

However, this is not the most precise way of doing this computation, and
the distance matrix returned by this function may not be exactly
symmetric as required by, e.g., `scipy.spatial.distance` functions.

Read more in the User Guide.

* **Parameters:**
  * **X** ( *{array-like* *,* *sparse matrix}* *,* *shape* *(**n_samples_1* *,* *n_features* *)*)
  * **Y** ( *{array-like* *,* *sparse matrix}* *,* *shape* *(**n_samples_2* *,* *n_features* *)*)
  * **Y_norm_squared** (*array-like* *,* *shape* *(**n_samples_2* *,*  *)* *,* *optional*) – Pre-computed dot-products of vectors in Y (e.g.,
    `(Y**2).sum(axis=1)`)
    May be ignored in some cases, see the note below.
  * **squared** (*boolean* *,* *optional*) – Return squared Euclidean distances.
  * **X_norm_squared** (*array-like* *,* *shape =* *[**n_samples_1* *]* *,* *optional*) – Pre-computed dot-products of vectors in X (e.g.,
    `(X**2).sum(axis=1)`)
    May be ignored in some cases, see the note below.

### Notes

To achieve better accuracy, X_norm_squared and Y_norm_squared may be
unused if they are passed as `float32`.

* **Returns:**
  **distances**
* **Return type:**
  tensor, shape (n_samples_1, n_samples_2)

### Examples

```pycon
>>> from maxframe.learn.metrics.pairwise import euclidean_distances
>>> X = [[0, 1], [1, 1]]
>>> # distance between rows of X
>>> euclidean_distances(X, X).execute()
array([[0., 1.],
       [1., 0.]])
>>> # get distance to origin
>>> euclidean_distances(X, [[0, 0]]).execute()
array([[1.        ],
       [1.41421356]])
```

#### SEE ALSO
`paired_distances`
: distances betweens pairs of elements of X and Y.
