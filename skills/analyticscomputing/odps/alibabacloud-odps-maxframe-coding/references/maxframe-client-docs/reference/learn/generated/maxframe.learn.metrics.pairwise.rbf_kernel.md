# maxframe.learn.metrics.pairwise.rbf_kernel

### maxframe.learn.metrics.pairwise.rbf_kernel(X, Y=None, gamma=None)

Compute the rbf (gaussian) kernel between X and Y:

```default
K(x, y) = exp(-gamma ||x-y||^2)
```

for each pair of rows x in X and y in Y.

Read more in the User Guide.

* **Parameters:**
  * **X** (*tensor* *of* *shape* *(**n_samples_X* *,* *n_features* *)*)
  * **Y** (*tensor* *of* *shape* *(**n_samples_Y* *,* *n_features* *)*)
  * **gamma** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *default None*) – If None, defaults to 1.0 / n_features
* **Returns:**
  **kernel_matrix**
* **Return type:**
  tensor of shape (n_samples_X, n_samples_Y)
