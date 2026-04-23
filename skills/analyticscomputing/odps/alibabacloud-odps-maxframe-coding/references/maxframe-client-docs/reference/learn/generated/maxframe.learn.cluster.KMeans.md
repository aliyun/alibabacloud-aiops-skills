# maxframe.learn.cluster.KMeans

### *class* maxframe.learn.cluster.KMeans(n_clusters=8, init='k-means||', n_init=1, max_iter=300, tol=0.0001, verbose=0, random_state=None, copy_x=True, algorithm='auto', oversampling_factor=2, init_iter=5)

K-Means clustering.

Read more in the User Guide.

* **Parameters:**
  * **n_clusters** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default=8*) – The number of clusters to form as well as the number of
    centroids to generate.
  * **init** ( *{'k-means++'* *,*  *'k-means* *|* *|* *'* *,*  *'random'}* *or* *tensor* *of* *shape*             *(**n_clusters* *,* *n_features* *)* *,* *default='k-means* *|* *|* *'*) – 

    Method for initialization, defaults to ‘k-means||’:

    ’k-means++’ : selects initial cluster centers for k-mean
    clustering in a smart way to speed up convergence. See section
    Notes in k_init for more details.

    ’k-means||’: scalable k-means++.

    ’random’: choose k observations (rows) at random from data for
    the initial centroids.

    If a tensor is passed, it should be of shape (n_clusters, n_features)
    and gives the initial centers.
  * **n_init** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default=1*) – Number of time the k-means algorithm will be run with different
    centroid seeds. The final results will be the best output of
    n_init consecutive runs in terms of inertia.
  * **max_iter** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default=300*) – Maximum number of iterations of the k-means algorithm for a
    single run.
  * **tol** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *default=1e-4*) – Relative tolerance with regards to inertia to declare convergence.
  * **verbose** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default=0*) – Verbosity mode.
  * **random_state** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *RandomState instance* *,* *default=None*) – Determines random number generation for centroid initialization. Use
    an int to make the randomness deterministic.
    See Glossary.
  * **copy_x** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default=True*) – When pre-computing distances it is more numerically accurate to center
    the data first.  If copy_x is True (default), then the original data is
    not modified, ensuring X is C-contiguous.  If False, the original data
    is modified, and put back before the function returns, but small
    numerical differences may be introduced by subtracting and then adding
    the data mean, in this case it will also not ensure that data is
    C-contiguous which may cause a significant slowdown.
  * **algorithm** ( *{"auto"* *,*  *"full"* *,*  *"elkan"}* *,* *default="auto"*) – K-means algorithm to use. The classical EM-style algorithm is “full”.
    The “elkan” variation is more efficient by using the triangle
    inequality, but currently doesn’t support sparse data. “auto” chooses
    “elkan” for dense data and “full” for sparse data.
  * **oversampling_factor** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default=2*) – Only work for kmeans||, used in each iteration in kmeans||.
  * **init_iter** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default=5*) – Only work for kmeans||, indicates how may iterations required.

#### cluster_centers_

Coordinates of cluster centers. If the algorithm stops before fully
converging (see `tol` and `max_iter`), these will not be
consistent with `labels_`.

* **Type:**
  tensor of shape (n_clusters, n_features)

#### labels_

Labels of each point

* **Type:**
  tensor of shape (n_samples,)

#### inertia_

Sum of squared distances of samples to their closest cluster center.

* **Type:**
  [float](https://docs.python.org/3/library/functions.html#float)

#### n_iter_

Number of iterations run.

* **Type:**
  [int](https://docs.python.org/3/library/functions.html#int)

#### SEE ALSO
`MiniBatchKMeans`
: Alternative online implementation that does incremental updates of the centers positions using mini-batches. For large scale learning (say n_samples > 10k) MiniBatchKMeans is probably much faster than the default batch implementation.

### Notes

The k-means problem is solved using either Lloyd’s or Elkan’s algorithm.

The average complexity is given by O(k n T), were n is the number of
samples and T is the number of iteration.

The worst case complexity is given by O(n^(k+2/p)) with
n = n_samples, p = n_features. (D. Arthur and S. Vassilvitskii,
‘How slow is the k-means method?’ SoCG2006)

In practice, the k-means algorithm is very fast (one of the fastest
clustering algorithms available), but it falls in local minima. That’s why
it can be useful to restart it several times.

If the algorithm stops before fully converging (because of `tol` or
`max_iter`), `labels_` and `cluster_centers_` will not be consistent,
i.e. the `cluster_centers_` will not be the means of the points in each
cluster. Also, the estimator will reassign `labels_` after the last
iteration to make `labels_` consistent with `predict` on the training
set.

### Examples

```pycon
>>> from maxframe.learn.cluster import KMeans
>>> import maxframe.tensor as mt
>>> X = mt.array([[1, 2], [1, 4], [1, 0],
...               [10, 2], [10, 4], [10, 0]])
>>> kmeans = KMeans(n_clusters=2, random_state=0, init='k-means++').fit(X).execute()
>>> kmeans.labels_
array([1, 1, 1, 0, 0, 0], dtype=int32)
>>> kmeans.predict([[0, 0], [12, 3]]).execute()
array([1, 0], dtype=int32)
>>> kmeans.cluster_centers_
array([[10.,  2.],
       [ 1.,  2.]])
```

#### \_\_init_\_(n_clusters=8, init='k-means||', n_init=1, max_iter=300, tol=0.0001, verbose=0, random_state=None, copy_x=True, algorithm='auto', oversampling_factor=2, init_iter=5)

### Methods

| [`__init__`](#maxframe.learn.cluster.KMeans.__init__)([n_clusters, init, n_init, ...])   |                                                                    |
|------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| `execute`([session, run_kwargs, extra_tileables])                                        |                                                                    |
| `fetch`([session, run_kwargs])                                                           |                                                                    |
| `fit`(X[, y, sample_weight, execute, session, ...])                                      | Compute k-means clustering.                                        |
| `fit_predict`(X[, y, execute, sample_weight, ...])                                       | Compute cluster centers and predict cluster index for each sample. |
| `fit_transform`(X[, y, sample_weight, ...])                                              | Compute clustering and transform X to cluster-distance space.      |
| `get_metadata_routing`()                                                                 | Get metadata routing of this object.                               |
| `get_params`([deep])                                                                     | Get parameters for this estimator.                                 |
| `predict`(X[, sample_weight, execute, ...])                                              | Predict the closest cluster each sample in X belongs to.           |
| `score`(X[, y, execute, sample_weight, ...])                                             | Opposite of the value of X on the K-means objective.               |
| `set_fit_request`(\*[, execute, run_kwargs, ...])                                        | Request metadata passed to the `fit` method.                       |
| `set_params`(\*\*params)                                                                 | Set the parameters of this estimator.                              |
| `set_predict_request`(\*[, execute, ...])                                                | Request metadata passed to the `predict` method.                   |
| `set_score_request`(\*[, execute, run_kwargs, ...])                                      | Request metadata passed to the `score` method.                     |
| `set_transform_request`(\*[, run_kwargs, session])                                       | Request metadata passed to the `transform` method.                 |
| `transform`(X[, session, run_kwargs])                                                    | Transform X to a cluster-distance space.                           |
