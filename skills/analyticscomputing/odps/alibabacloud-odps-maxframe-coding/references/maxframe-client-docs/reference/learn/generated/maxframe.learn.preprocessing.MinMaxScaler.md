# maxframe.learn.preprocessing.MinMaxScaler

### *class* maxframe.learn.preprocessing.MinMaxScaler(feature_range=(0, 1), copy=True, clip=False, validate=True)

Transform features by scaling each feature to a given range.

This estimator scales and translates each feature individually such
that it is in the given range on the training set, e.g. between
zero and one.

The transformation is given by:

```default
X_std = (X - X.min(axis=0)) / (X.max(axis=0) - X.min(axis=0))
X_scaled = X_std * (max - min) + min
```

where min, max = feature_range.

This transformation is often used as an alternative to zero mean,
unit variance scaling.

Read more in the User Guide.

* **Parameters:**
  * **feature_range** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *(**min* *,* *max* *)* *,* *default=* *(**0* *,* *1* *)*) – Desired range of transformed data.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default=True*) – Set to False to perform inplace row normalization and avoid a
    copy (if the input is already a numpy array).
  * **clip** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default=False*) – Set to True to clip transformed values of held-out data to
    provided feature range.

#### min_

Per feature adjustment for minimum. Equivalent to
`min - X.min(axis=0) * self.scale_`

* **Type:**
  Tensor of shape (n_features,)

#### scale_

Per feature relative scaling of the data. Equivalent to
`(max - min) / (X.max(axis=0) - X.min(axis=0))`

* **Type:**
  Tensor of shape (n_features,)

#### data_min_

Per feature minimum seen in the data

* **Type:**
  ndarray of shape (n_features,)

#### data_max_

Per feature maximum seen in the data

* **Type:**
  ndarray of shape (n_features,)

#### data_range_

Per feature range `(data_max_ - data_min_)` seen in the data

* **Type:**
  ndarray of shape (n_features,)

#### n_samples_seen_

The number of samples processed by the estimator.
It will be reset on new calls to fit, but increments across
`partial_fit` calls.

* **Type:**
  [int](https://docs.python.org/3/library/functions.html#int)

### Examples

```pycon
>>> from maxframe.learn.preprocessing import MinMaxScaler
>>> data = [[-1, 2], [-0.5, 6], [0, 10], [1, 18]]
>>> scaler = MinMaxScaler()
>>> print(scaler.fit(data))
MinMaxScaler()
>>> print(scaler.data_max_)
[ 1. 18.]
>>> print(scaler.transform(data))
[[0.   0.  ]
 [0.25 0.25]
 [0.5  0.5 ]
 [1.   1.  ]]
>>> print(scaler.transform([[2, 2]]))
[[1.5 0. ]]
```

#### SEE ALSO
[`minmax_scale`](maxframe.learn.preprocessing.minmax_scale.md#maxframe.learn.preprocessing.minmax_scale)
: Equivalent function without the estimator API.

### Notes

NaNs are treated as missing values: disregarded in fit, and maintained in
transform.

For a comparison of the different scalers, transformers, and normalizers,
see examples/preprocessing/plot_all_scaling.py.

#### \_\_init_\_(feature_range=(0, 1), copy=True, clip=False, validate=True)

### Methods

| [`__init__`](#maxframe.learn.preprocessing.MinMaxScaler.__init__)([feature_range, copy, clip, validate])   |                                                               |
|------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| `execute`([session, run_kwargs, extra_tileables])                                                          |                                                               |
| `fetch`([session, run_kwargs])                                                                             |                                                               |
| `fit`(X[, y, execute, session, run_kwargs])                                                                | Compute the minimum and maximum to be used for later scaling. |
| `fit_transform`(X[, y])                                                                                    | Fit to data, then transform it.                               |
| `get_metadata_routing`()                                                                                   | Get metadata routing of this object.                          |
| `get_params`([deep])                                                                                       | Get parameters for this estimator.                            |
| `inverse_transform`(X[, execute, session, ...])                                                            | Undo the scaling of X according to feature_range.             |
| `partial_fit`(X[, y, execute, session, run_kwargs])                                                        | Online computation of min and max on X for later scaling.     |
| `set_fit_request`(\*[, execute, run_kwargs, ...])                                                          | Request metadata passed to the `fit` method.                  |
| `set_inverse_transform_request`(\*[, execute, ...])                                                        | Request metadata passed to the `inverse_transform` method.    |
| `set_params`(\*\*params)                                                                                   | Set the parameters of this estimator.                         |
| `set_partial_fit_request`(\*[, execute, ...])                                                              | Request metadata passed to the `partial_fit` method.          |
| `set_transform_request`(\*[, execute, ...])                                                                | Request metadata passed to the `transform` method.            |
| `transform`(X[, execute, session, run_kwargs])                                                             | Scale features of X according to feature_range.               |
