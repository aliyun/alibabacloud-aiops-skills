# maxframe.learn.metrics.pairwise.cosine_distances

### maxframe.learn.metrics.pairwise.cosine_distances(X, Y=None)

Compute cosine distance between samples in X and Y.

Cosine distance is defined as 1.0 minus the cosine similarity.

Read more in the User Guide.

* **Parameters:**
  * **X** (*array_like* *,* *sparse matrix*) – with shape (n_samples_X, n_features).
  * **Y** (*array_like* *,* *sparse matrix* *(**optional* *)*) – with shape (n_samples_Y, n_features).
* **Returns:**
  **distance matrix** – A tensor with shape (n_samples_X, n_samples_Y).
* **Return type:**
  Tensor

#### SEE ALSO
[`maxframe.learn.metrics.pairwise.cosine_similarity`](maxframe.learn.metrics.pairwise.cosine_similarity.md#maxframe.learn.metrics.pairwise.cosine_similarity)

`maxframe.tensor.spatial.distance.cosine`
: dense matrices only
