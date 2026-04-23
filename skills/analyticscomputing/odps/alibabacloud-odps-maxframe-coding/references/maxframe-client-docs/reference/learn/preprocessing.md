<a id="learn-preprocessing-ref"></a>

# Preprocessing

## Transform Classes

| [`preprocessing.LabelBinarizer`](generated/maxframe.learn.preprocessing.LabelBinarizer.md#maxframe.learn.preprocessing.LabelBinarizer)(\*[, neg_label, ...])   | Binarize labels in a one-vs-all fashion.                                |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`preprocessing.LabelEncoder`](generated/maxframe.learn.preprocessing.LabelEncoder.md#maxframe.learn.preprocessing.LabelEncoder)()                             | Encode target labels with value between 0 and n_classes-1.              |
| [`preprocessing.MinMaxScaler`](generated/maxframe.learn.preprocessing.MinMaxScaler.md#maxframe.learn.preprocessing.MinMaxScaler)([feature_range, ...])         | Transform features by scaling each feature to a given range.            |
| [`preprocessing.StandardScaler`](generated/maxframe.learn.preprocessing.StandardScaler.md#maxframe.learn.preprocessing.StandardScaler)(\*[, copy, ...])        | Standardize features by removing the mean and scaling to unit variance. |

## Transform Functions

| [`preprocessing.label_binarize`](generated/maxframe.learn.preprocessing.label_binarize.md#maxframe.learn.preprocessing.label_binarize)(y, \*, classes)   | Binarize labels in a one-vs-all fashion.                       |
|----------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| [`preprocessing.minmax_scale`](generated/maxframe.learn.preprocessing.minmax_scale.md#maxframe.learn.preprocessing.minmax_scale)(X[, ...])               | Transform features by scaling each feature to a given range.   |
| [`preprocessing.normalize`](generated/maxframe.learn.preprocessing.normalize.md#maxframe.learn.preprocessing.normalize)(X[, norm, axis, ...])            | Scale input vectors individually to unit norm (vector length). |
| [`preprocessing.scale`](generated/maxframe.learn.preprocessing.scale.md#maxframe.learn.preprocessing.scale)(X, \*[, axis, with_mean, ...])               | Standardize a dataset along any axis.                          |
