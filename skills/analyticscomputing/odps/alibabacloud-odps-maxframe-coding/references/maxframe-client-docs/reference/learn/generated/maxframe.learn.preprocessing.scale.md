# maxframe.learn.preprocessing.scale

### maxframe.learn.preprocessing.scale(X, , axis=0, with_mean=True, with_std=True, copy=True, validate=True)

Standardize a dataset along any axis.

Center to the mean and component wise scale to unit variance.

Read more in the User Guide.

* **Parameters:**
  * **X** ( *{array-like* *,* *sparse matrix}* *of* *shape* *(**n_samples* *,* *n_features* *)*) – The data to center and scale.
  * **axis** ( *{0* *,* *1}* *,* *default=0*) – Axis used to compute the means and standard deviations along. If 0,
    independently standardize each feature, otherwise (if 1) standardize
    each sample.
  * **with_mean** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default=True*) – If True, center the data before scaling.
  * **with_std** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default=True*) – If True, scale the data to unit variance (or equivalently,
    unit standard deviation).
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default=True*) – If False, try to avoid a copy and scale in place.
    This is not guaranteed to always work in place; e.g. if the data is
    a numpy array with an int dtype, a copy will be returned even with
    copy=False.
* **Returns:**
  **X_tr** – The transformed data.
* **Return type:**
  {ndarray, sparse matrix} of shape (n_samples, n_features)

#### SEE ALSO
[`StandardScaler`](maxframe.learn.preprocessing.StandardScaler.md#maxframe.learn.preprocessing.StandardScaler)
: Performs scaling to unit variance using the Transformer API (e.g. as part of a preprocessing `Pipeline`).

### Notes

This implementation will refuse to center scipy.sparse matrices
since it would make them non-sparse and would potentially crash the
program with memory exhaustion problems.

Instead the caller is expected to either set explicitly
with_mean=False (in that case, only variance scaling will be
performed on the features of the CSC matrix) or to call X.toarray()
if he/she expects the materialized dense array to fit in memory.

To avoid memory copy the caller should pass a CSC matrix.

NaNs are treated as missing values: disregarded to compute the statistics,
and maintained during the data transformation.

We use a biased estimator for the standard deviation, equivalent to
numpy.std(x, ddof=0). Note that the choice of ddof is unlikely to
affect model performance.

For a comparison of the different scalers, transformers, and normalizers,
see: sphx_glr_auto_examples_preprocessing_plot_all_scaling.py.

#### WARNING
Risk of data leak

Do not use `scale()` unless you know
what you are doing. A common mistake is to apply it to the entire data
*before* splitting into training and test sets. This will bias the
model evaluation because information would have leaked from the test
set to the training set.
In general, we recommend using
`StandardScaler` within a
Pipeline in order to prevent most risks of data
leaking: pipe = make_pipeline(StandardScaler(), LogisticRegression()).

### Examples

```pycon
>>> from maxframe.learn.preprocessing import scale
>>> X = [[-2, 1, 2], [-1, 0, 1]]
>>> scale(X, axis=0).execute()  # scaling each column independently
array([[-1.,  1.,  1.],
       [ 1., -1., -1.]])
>>> scale(X, axis=1).execute()  # scaling each row independently
array([[-1.37...,  0.39...,  0.98...],
       [-1.22...,  0.     ,  1.22...]])
```
