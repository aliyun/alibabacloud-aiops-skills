# maxframe.learn.metrics.pairwise.cosine_similarity

### maxframe.learn.metrics.pairwise.cosine_similarity(X, Y=None, dense_output=True)

Compute cosine similarity between samples in X and Y.

Cosine similarity, or the cosine kernel, computes similarity as the
normalized dot product of X and Y:

> K(X, Y) = <X, Y> / (||X||\*||Y||)

On L2-normalized data, this function is equivalent to linear_kernel.

Read more in the User Guide.

* **Parameters:**
  * **X** (*Tensor* *or* *sparse tensor* *,* *shape:* *(**n_samples_X* *,* *n_features* *)*) – Input data.
  * **Y** (*Tensor* *or* *sparse tensor* *,* *shape:* *(**n_samples_Y* *,* *n_features* *)*) – Input data. If `None`, the output will be the pairwise
    similarities between all samples in `X`.
  * **dense_output** (*boolean* *(**optional* *)* *,* *default True*) – Whether to return dense output even when the input is sparse. If
    `False`, the output is sparse if both input tensors are sparse.
* **Returns:**
  **kernel matrix** – A tensor with shape (n_samples_X, n_samples_Y).
* **Return type:**
  Tensor
