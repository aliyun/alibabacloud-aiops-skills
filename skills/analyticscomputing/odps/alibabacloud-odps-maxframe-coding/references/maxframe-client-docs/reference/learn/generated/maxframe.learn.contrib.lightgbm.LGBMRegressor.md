# maxframe.learn.contrib.lightgbm.LGBMRegressor

### *class* maxframe.learn.contrib.lightgbm.LGBMRegressor(\*args, \*\*kwargs)

#### \_\_init_\_(\*args, \*\*kwargs)

Construct a gradient boosting model.

* **Parameters:**
  * **boosting_type** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional* *(**default='gbdt'* *)*) – ‘gbdt’, traditional Gradient Boosting Decision Tree.
    ‘dart’, Dropouts meet Multiple Additive Regression Trees.
    ‘goss’, Gradient-based One-Side Sampling.
    ‘rf’, Random Forest.
  * **num_leaves** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional* *(**default=31* *)*) – Maximum tree leaves for base learners.
  * **max_depth** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional* *(**default=-1* *)*) – Maximum tree depth for base learners, <=0 means no limit.
  * **learning_rate** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional* *(**default=0.1* *)*) – Boosting learning rate.
    You can use `callbacks` parameter of `fit` method to shrink/adapt learning rate
    in training using `reset_parameter` callback.
    Note, that this will ignore the `learning_rate` argument in training.
  * **n_estimators** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional* *(**default=100* *)*) – Number of boosted trees to fit.
  * **subsample_for_bin** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional* *(**default=200000* *)*) – Number of samples for constructing bins.
  * **objective** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *callable* *or* *None* *,* *optional* *(**default=None* *)*) – Specify the learning task and the corresponding learning objective or
    a custom objective function to be used (see note below).
    Default: ‘regression’ for LGBMRegressor, ‘binary’ or ‘multiclass’ for LGBMClassifier, ‘lambdarank’ for LGBMRanker.
  * **class_weight** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *,*  *'balanced'* *or* *None* *,* *optional* *(**default=None* *)*) – Weights associated with classes in the form `{class_label: weight}`.
    Use this parameter only for multi-class classification task;
    for binary classification task you may use `is_unbalance` or `scale_pos_weight` parameters.
    Note, that the usage of all these parameters will result in poor estimates of the individual class probabilities.
    You may want to consider performing probability calibration
    ([https://scikit-learn.org/stable/modules/calibration.html](https://scikit-learn.org/stable/modules/calibration.html)) of your model.
    The ‘balanced’ mode uses the values of y to automatically adjust weights
    inversely proportional to class frequencies in the input data as `n_samples / (n_classes * np.bincount(y))`.
    If None, all classes are supposed to have weight one.
    Note, that these weights will be multiplied with `sample_weight` (passed through the `fit` method)
    if `sample_weight` is specified.
  * **min_split_gain** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional* *(**default=0.* *)*) – Minimum loss reduction required to make a further partition on a leaf node of the tree.
  * **min_child_weight** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional* *(**default=1e-3* *)*) – Minimum sum of instance weight (hessian) needed in a child (leaf).
  * **min_child_samples** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional* *(**default=20* *)*) – Minimum number of data needed in a child (leaf).
  * **subsample** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional* *(**default=1.* *)*) – Subsample ratio of the training instance.
  * **subsample_freq** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional* *(**default=0* *)*) – Frequency of subsample, <=0 means no enable.
  * **colsample_bytree** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional* *(**default=1.* *)*) – Subsample ratio of columns when constructing each tree.
  * **reg_alpha** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional* *(**default=0.* *)*) – L1 regularization term on weights.
  * **reg_lambda** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional* *(**default=0.* *)*) – L2 regularization term on weights.
  * **random_state** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *RandomState object* *or* *None* *,* *optional* *(**default=None* *)*) – Random number seed.
    If int, this number is used to seed the C++ code.
    If RandomState object (numpy), a random integer is picked based on its state to seed the C++ code.
    If None, default seeds in C++ code are used.
  * **n_jobs** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional* *(**default=-1* *)*) – Number of parallel threads.
  * **silent** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional* *(**default=True* *)*) – Whether to print messages while running boosting.
  * **importance_type** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional* *(**default='split'* *)*) – The type of feature importance to be filled into `feature_importances_`.
    If ‘split’, result contains numbers of times the feature is used in a model.
    If ‘gain’, result contains total gains of splits which use the feature.
  * **\*\*kwargs** – 

    Other parameters for the model.
    Check [http://lightgbm.readthedocs.io/en/latest/Parameters.html](http://lightgbm.readthedocs.io/en/latest/Parameters.html) for more parameters.

    #### WARNING
    \*\*kwargs is not supported in sklearn, it may cause unexpected issues.

#### NOTE
A custom objective function can be provided for the `objective` parameter.
In this case, it should have the signature
`objective(y_true, y_pred) -> grad, hess` or
`objective(y_true, y_pred, group) -> grad, hess`:

> y_true
> : The target values.

> y_pred
> : The predicted values.
>   Predicted values are returned before any transformation,
>   e.g. they are raw margin instead of probability of positive class for binary task.

> group
> : Group/query data.
>   Only used in the learning-to-rank task.
>   sum(group) = n_samples.
>   For example, if you have a 100-document dataset with `group = [10, 20, 40, 10, 10, 10]`, that means that you have 6 groups,
>   where the first 10 records are in the first group, records 11-30 are in the second group, records 31-70 are in the third group, etc.

> grad
> : The value of the first order derivative (gradient) of the loss
>   with respect to the elements of y_pred for each sample point.

> hess
> : The value of the second order derivative (Hessian) of the loss
>   with respect to the elements of y_pred for each sample point.

For multi-class task, the y_pred is group by class_id first, then group by row_id.
If you want to get i-th row y_pred in j-th class, the access way is y_pred[j \* num_data + i]
and you should group grad and hess in this way as well.

### Methods

| [`__init__`](#maxframe.learn.contrib.lightgbm.LGBMRegressor.__init__)(\*args, \*\*kwargs)   | Construct a gradient boosting model.                       |
|---------------------------------------------------------------------------------------------|------------------------------------------------------------|
| `execute`([session, run_kwargs])                                                            |                                                            |
| `fetch`([session, run_kwargs])                                                              |                                                            |
| `fit`(X, y, \*[, sample_weight, init_score, ...])                                           | unsupported features: 1.                                   |
| `get_metadata_routing`()                                                                    | Get metadata routing of this object.                       |
| `get_params`([deep])                                                                        | Get parameters for this estimator.                         |
| `predict`(X[, raw_score, start_iteration, ...])                                             | Return the predicted value for each sample.                |
| `score`(X, y[, sample_weight])                                                              | Return the coefficient of determination of the prediction. |
| `set_fit_request`(\*[, callbacks, ...])                                                     | Request metadata passed to the `fit` method.               |
| `set_params`(\*\*params)                                                                    | Set the parameters of this estimator.                      |
| `set_predict_request`(\*[, num_iteration, ...])                                             | Request metadata passed to the `predict` method.           |
| `set_score_request`(\*[, sample_weight])                                                    | Request metadata passed to the `score` method.             |

### Attributes

| `best_iteration_`      | The best iteration of fitted model if `early_stopping()` callback has been specified.   |
|------------------------|-----------------------------------------------------------------------------------------|
| `best_score_`          | The best score of fitted model.                                                         |
| `booster_`             | The underlying Booster of this model.                                                   |
| `evals_result_`        | The evaluation results if validation sets have been specified.                          |
| `feature_importances_` | The feature importances (the higher, the more important).                               |
| `feature_name_`        | The names of features.                                                                  |
| `n_features_`          | The number of features of fitted model.                                                 |
| `n_features_in_`       | The number of features of fitted model.                                                 |
| `objective_`           | The concrete objective used while fitting this model.                                   |
