# maxframe.learn.contrib.xgboost.XGBClassifier

### *class* maxframe.learn.contrib.xgboost.XGBClassifier(xgb_model: XGBClassifier | Booster = None, \*\*kwargs)

Implementation of the scikit-learn API for XGBoost classification.

#### \_\_init_\_(xgb_model: XGBClassifier | Booster = None, \*\*kwargs)

### Methods

| [`__init__`](#maxframe.learn.contrib.xgboost.XGBClassifier.__init__)([xgb_model])   |                                                             |
|-------------------------------------------------------------------------------------|-------------------------------------------------------------|
| `apply`(X[, iteration_range])                                                       | Return the predicted leaf every tree for each sample.       |
| `evals_result`(\*\*kw)                                                              | Return the evaluation results.                              |
| `execute`([session, run_kwargs])                                                    |                                                             |
| `fetch`([session, run_kwargs])                                                      |                                                             |
| `fit`(X, y[, sample_weight, base_margin, ...])                                      | Fit gradient boosting model.                                |
| `get_booster`()                                                                     | Get the underlying xgboost Booster of this model.           |
| `get_metadata_routing`()                                                            | Get metadata routing of this object.                        |
| `get_num_boosting_rounds`()                                                         | Gets the number of xgboost boosting rounds.                 |
| `get_params`([deep])                                                                | Get parameters.                                             |
| `get_xgb_params`()                                                                  | Get xgboost specific parameters.                            |
| `load_model`(fname)                                                                 | Load the model from a file or bytearray.                    |
| `predict`(data, \*\*kw)                                                             | Predict with data.                                          |
| `predict_proba`(data[, ntree_limit, flag])                                          |                                                             |
| `save_model`(fname)                                                                 | Save the model to a file.                                   |
| `score`(X, y[, sample_weight])                                                      | Return the mean accuracy on the given test data and labels. |
| `set_fit_request`(\*[, base_margin, ...])                                           | Request metadata passed to the `fit` method.                |
| `set_params`(\*\*params)                                                            | Set the parameters of this estimator.                       |
| `set_predict_proba_request`(\*[, data, flag, ...])                                  | Request metadata passed to the `predict_proba` method.      |
| `set_predict_request`(\*[, data])                                                   | Request metadata passed to the `predict` method.            |
| `set_score_request`(\*[, sample_weight])                                            | Request metadata passed to the `score` method.              |
| `to_odps_model`(model_name[, model_version, ...])                                   | Save trained model to MaxCompute.                           |

### Attributes

| `best_iteration`       | The best iteration obtained by early stopping.                             |
|------------------------|----------------------------------------------------------------------------|
| `best_score`           | The best score obtained by early stopping.                                 |
| `classes_`             |                                                                            |
| `coef_`                | Coefficients property                                                      |
| `feature_importances_` | Feature importances property, return depends on importance_type parameter. |
| `feature_names_in_`    | Names of features seen during `fit()`.                                     |
| `intercept_`           | Intercept (bias) property                                                  |
| `n_features_in_`       | Number of features seen during `fit()`.                                    |
| `training_info_`       |                                                                            |
