<a id="learn-xgboost-ref"></a>

# XGBoost Integration

## Data Structure

| [`xgboost.DMatrix`](generated/maxframe.learn.contrib.xgboost.DMatrix.md#maxframe.learn.contrib.xgboost.DMatrix)(data[, label, missing, ...])   |    |
|------------------------------------------------------------------------------------------------------------------------------------------------|----|

## Training

| [`xgboost.predict`](generated/maxframe.learn.contrib.xgboost.predict.md#maxframe.learn.contrib.xgboost.predict)(model, data[, ...])     | Using MaxFrame XGBoost model to predict data.   |
|-----------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------|
| [`xgboost.train`](generated/maxframe.learn.contrib.xgboost.train.md#maxframe.learn.contrib.xgboost.train)(params, dtrain[, evals, ...]) | Train XGBoost model in MaxFrame manner.         |

## Callbacks

| [`xgboost.callback.EarlyStopping`](generated/maxframe.learn.contrib.xgboost.callback.EarlyStopping.md#maxframe.learn.contrib.xgboost.callback.EarlyStopping)(\*, rounds[, ...])           |    |
|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----|
| [`xgboost.callback.LearningRateScheduler`](generated/maxframe.learn.contrib.xgboost.callback.LearningRateScheduler.md#maxframe.learn.contrib.xgboost.callback.LearningRateScheduler)(...) |    |

## Scikit-learn API

| [`xgboost.XGBClassifier`](generated/maxframe.learn.contrib.xgboost.XGBClassifier.md#maxframe.learn.contrib.xgboost.XGBClassifier)([xgb_model])   | Implementation of the scikit-learn API for XGBoost classification.   |
|--------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [`xgboost.XGBRegressor`](generated/maxframe.learn.contrib.xgboost.XGBRegressor.md#maxframe.learn.contrib.xgboost.XGBRegressor)([xgb_model])      | Implementation of the scikit-learn API for XGBoost regressor.        |
