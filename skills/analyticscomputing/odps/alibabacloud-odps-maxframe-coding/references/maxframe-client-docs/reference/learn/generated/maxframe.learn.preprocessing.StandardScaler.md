# maxframe.learn.preprocessing.StandardScaler

### *class* maxframe.learn.preprocessing.StandardScaler(, copy=True, with_mean=True, with_std=True, validate=True)

Standardize features by removing the mean and scaling to unit variance.

The standard score of a sample x is calculated as:

```text
z = (x - u) / s
```

where u is the mean of the training samples or zero if with_mean=False,
and s is the standard deviation of the training samples or one if
with_std=False.

Centering and scaling happen independently on each feature by computing
the relevant statistics on the samples in the training set. Mean and
standard deviation are then stored to be used on later data using
`transform()`.

Standardization of a dataset is a common requirement for many
machine learning estimators: they might behave badly if the
individual features do not more or less look like standard normally
distributed data (e.g. Gaussian with 0 mean and unit variance).

For instance many elements used in the objective function of
a learning algorithm (such as the RBF kernel of Support Vector
Machines or the L1 and L2 regularizers of linear models) assume that
all features are centered around 0 and have variance in the same
order. If a feature has a variance that is orders of magnitude larger
than others, it might dominate the objective function and make the
estimator unable to learn from other features correctly as expected.

StandardScaler is sensitive to outliers, and the features may scale
differently from each other in the presence of outliers. For an example
visualization, refer to Compare StandardScaler with other scalers.

This scaler can also be applied to sparse CSR or CSC matrices by passing
with_mean=False to avoid breaking the sparsity structure of the data.

Read more in the User Guide.

* **Parameters:**
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default=True*) – If False, try to avoid a copy and do inplace scaling instead.
    This is not guaranteed to always work inplace; e.g. if the data is
    not a NumPy array or scipy.sparse CSR matrix, a copy may still be
    returned.
  * **with_mean** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default=True*) – If True, center the data before scaling.
    This does not work (and will raise an exception) when attempted on
    sparse matrices, because centering them entails building a dense
    matrix which in common use cases is likely to be too large to fit in
    memory.
  * **with_std** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default=True*) – If True, scale the data to unit variance (or equivalently,
    unit standard deviation).

#### scale_

Per feature relative scaling of the data to achieve zero mean and unit
variance. Generally this is calculated using np.sqrt(var_). If a
variance is zero, we can’t achieve unit variance, and the data is left
as-is, giving a scaling factor of 1. scale_ is equal to None
when with_std=False.

* **Type:**
  ndarray of shape (n_features,) or None

#### mean_

The mean value for each feature in the training set.
Equal to `None` when `with_mean=False` and `with_std=False`.

* **Type:**
  ndarray of shape (n_features,) or None

#### var_

The variance for each feature in the training set. Used to compute
scale_. Equal to `None` when `with_mean=False` and
`with_std=False`.

* **Type:**
  ndarray of shape (n_features,) or None

#### n_features_in_

Number of features seen during fit.

* **Type:**
  [int](https://docs.python.org/3/library/functions.html#int)

#### feature_names_in_

Names of features seen during fit. Defined only when X
has feature names that are all strings.

* **Type:**
  ndarray of shape (n_features_in_,)

#### n_samples_seen_

The number of samples processed by the estimator for each feature.
If there are no missing samples, the `n_samples_seen` will be an
integer, otherwise it will be an array of dtype int. If
sample_weights are used it will be a float (if no missing data)
or an array of dtype float that sums the weights seen so far.
Will be reset on new calls to fit, but increments across
`partial_fit` calls.

* **Type:**
  [int](https://docs.python.org/3/library/functions.html#int) or ndarray of shape (n_features,)

#### SEE ALSO
[`scale`](maxframe.learn.preprocessing.scale.md#maxframe.learn.preprocessing.scale)
: Equivalent function without the estimator API.

`PCA`
: Further removes the linear correlation across features with ‘whiten=True’.

### Notes

NaNs are treated as missing values: disregarded in fit, and maintained in
transform.

We use a biased estimator for the standard deviation, equivalent to
numpy.std(x, ddof=0). Note that the choice of ddof is unlikely to
affect model performance.

### Examples

```pycon
>>> from maxframe.learn.preprocessing import StandardScaler
>>> data = [[0, 0], [0, 0], [1, 1], [1, 1]]
>>> scaler = StandardScaler()
>>> print(scaler.fit(data))
StandardScaler()
>>> print(scaler.mean_.execute())
[0.5 0.5]
>>> print(scaler.transform(data).execute())
[[-1. -1.]
 [-1. -1.]
 [ 1.  1.]
 [ 1.  1.]]
>>> print(scaler.transform([[2, 2]]).execute())
[[3. 3.]]
```

#### \_\_init_\_(, copy=True, with_mean=True, with_std=True, validate=True)

### Methods

| [`__init__`](#maxframe.learn.preprocessing.StandardScaler.__init__)(\*[, copy, with_mean, with_std, ...])   |                                                            |
|-------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| `execute`([session, run_kwargs, extra_tileables])                                                           |                                                            |
| `fetch`([session, run_kwargs])                                                                              |                                                            |
| `fit`(X[, y, sample_weight, execute, session, ...])                                                         | Compute the mean and std to be used for later scaling.     |
| `fit_transform`(X[, y])                                                                                     | Fit to data, then transform it.                            |
| `get_metadata_routing`()                                                                                    | Get metadata routing of this object.                       |
| `get_params`([deep])                                                                                        | Get parameters for this estimator.                         |
| `inverse_transform`(X[, copy, execute, ...])                                                                | Scale back the data to the original representation.        |
| `partial_fit`(X[, y, sample_weight, execute, ...])                                                          | Online computation of mean and std on X for later scaling. |
| `set_fit_request`(\*[, execute, run_kwargs, ...])                                                           | Request metadata passed to the `fit` method.               |
| `set_inverse_transform_request`(\*[, copy, ...])                                                            | Request metadata passed to the `inverse_transform` method. |
| `set_params`(\*\*params)                                                                                    | Set the parameters of this estimator.                      |
| `set_partial_fit_request`(\*[, execute, ...])                                                               | Request metadata passed to the `partial_fit` method.       |
| `set_transform_request`(\*[, copy, execute, ...])                                                           | Request metadata passed to the `transform` method.         |
| `transform`(X[, copy, execute, session, ...])                                                               | Perform standardization by centering and scaling.          |
