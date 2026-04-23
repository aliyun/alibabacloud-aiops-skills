# maxframe.learn.cluster.k_means

### maxframe.learn.cluster.k_means(X, n_clusters, sample_weight=None, init='k-means||', n_init=10, max_iter=300, verbose=False, tol=0.0001, random_state=None, copy_x=True, algorithm='auto', oversampling_factor=2, init_iter=5, return_n_iter=False)

K-means clustering algorithm.

* **Parameters:**
  * **X** (*Tensor* *,* *shape* *(**n_samples* *,* *n_features* *)*) – The observations to cluster. It must be noted that the data
    will be converted to C ordering, which will cause a memory copy
    if the given data is not C-contiguous.
  * **n_clusters** ([*int*](https://docs.python.org/3/library/functions.html#int)) – The number of clusters to form as well as the number of
    centroids to generate.
  * **sample_weight** (*array-like* *,* *shape* *(**n_samples* *,* *)* *,* *optional*) – The weights for each observation in X. If None, all observations
    are assigned equal weight (default: None)
  * **init** ( *{'k-means++'* *,*  *'k-means* *|* *|* *'* *,*  *'random'* *, or* *tensor* *, or* *a callable}* *,* *optional*) – 

    Method for initialization, default to ‘k-means||’:

    ’k-means++’ : selects initial cluster centers for k-mean
    clustering in a smart way to speed up convergence. See section
    Notes in k_init for more details.

    ’k-means||’: scalable k-means++.

    ’random’: choose k observations (rows) at random from data for
    the initial centroids.

    If an ndarray is passed, it should be of shape (n_clusters, n_features)
    and gives the initial centers.

    If a callable is passed, it should take arguments X, k and
    and a random state and return an initialization.
  * **n_init** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional* *,* *default: 10*) – Number of time the k-means algorithm will be run with different
    centroid seeds. The final results will be the best output of
    n_init consecutive runs in terms of inertia.
  * **max_iter** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional* *,* *default 300*) – Maximum number of iterations of the k-means algorithm to run.
  * **verbose** (*boolean* *,* *optional*) – Verbosity mode.
  * **tol** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional*) – The relative increment in the results before declaring convergence.
  * **random_state** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *RandomState instance* *or* *None* *(**default* *)*) – Determines random number generation for centroid initialization. Use
    an int to make the randomness deterministic.
    See Glossary.
  * **copy_x** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – When pre-computing distances it is more numerically accurate to center
    the data first.  If copy_x is True (default), then the original data is
    not modified, ensuring X is C-contiguous.  If False, the original data
    is modified, and put back before the function returns, but small
    numerical differences may be introduced by subtracting and then adding
    the data mean, in this case it will also not ensure that data is
    C-contiguous which may cause a significant slowdown.
  * **algorithm** ( *"auto"* *,*  *"full"* *or*  *"elkan"* *,* *default="auto"*) – K-means algorithm to use. The classical EM-style algorithm is “full”.
    The “elkan” variation is more efficient by using the triangle
    inequality, but currently doesn’t support sparse data. “auto” chooses
    “elkan” for dense data and “full” for sparse data.
  * **oversampling_factor** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default=2*) – Only work for kmeans||, used in each iteration in kmeans||.
  * **init_iter** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default=5*) – Only work for kmeans||, indicates how may iterations required.
  * **return_n_iter** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Whether or not to return the number of iterations.
* **Returns:**
  * **centroid** (*float ndarray with shape (k, n_features)*) – Centroids found at the last iteration of k-means.
  * **label** (*integer ndarray with shape (n_samples,)*) – label[i] is the code or index of the centroid the
    i’th observation is closest to.
  * **inertia** (*float*) – The final value of the inertia criterion (sum of squared distances to
    the closest centroid for all observations in the training set).
  * **best_n_iter** (*int*) – Number of iterations corresponding to the best results.
    Returned only if return_n_iter is set to True.
