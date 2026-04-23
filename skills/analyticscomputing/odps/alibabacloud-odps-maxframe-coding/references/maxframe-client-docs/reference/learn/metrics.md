<a id="learn-metrics-ref"></a>

# Metrics

## Classification Metrics

| [`metrics.accuracy_score`](generated/maxframe.learn.metrics.accuracy_score.md#maxframe.learn.metrics.accuracy_score)(y_true, y_pred[, ...])                                  | Accuracy classification score.                                                                   |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| [`metrics.auc`](generated/maxframe.learn.metrics.auc.md#maxframe.learn.metrics.auc)(x, y[, execute, session, run_kwargs])                                                    | Compute Area Under the Curve (AUC) using the trapezoidal rule                                    |
| [`metrics.f1_score`](generated/maxframe.learn.metrics.f1_score.md#maxframe.learn.metrics.f1_score)(y_true, y_pred, \*[, ...])                                                | Compute the F1 score, also known as balanced F-score or F-measure                                |
| [`metrics.fbeta_score`](generated/maxframe.learn.metrics.fbeta_score.md#maxframe.learn.metrics.fbeta_score)(y_true, y_pred, \*, beta)                                        | Compute the F-beta score                                                                         |
| [`metrics.log_loss`](generated/maxframe.learn.metrics.log_loss.md#maxframe.learn.metrics.log_loss)(y_true, y_pred, \*[, eps, ...])                                           | Log loss, aka logistic loss or cross-entropy loss.                                               |
| [`metrics.multilabel_confusion_matrix`](generated/maxframe.learn.metrics.multilabel_confusion_matrix.md#maxframe.learn.metrics.multilabel_confusion_matrix)(y_true, ...)     | Compute a confusion matrix for each class or sample.                                             |
| [`metrics.precision_recall_fscore_support`](generated/maxframe.learn.metrics.precision_recall_fscore_support.md#maxframe.learn.metrics.precision_recall_fscore_support)(...) | Compute precision, recall, F-measure and support for each class                                  |
| [`metrics.precision_score`](generated/maxframe.learn.metrics.precision_score.md#maxframe.learn.metrics.precision_score)(y_true, y_pred, \*[, ...])                           | Compute the precision                                                                            |
| [`metrics.recall_score`](generated/maxframe.learn.metrics.recall_score.md#maxframe.learn.metrics.recall_score)(y_true, y_pred, \*[, ...])                                    | Compute the recall                                                                               |
| [`metrics.roc_auc_score`](generated/maxframe.learn.metrics.roc_auc_score.md#maxframe.learn.metrics.roc_auc_score)(y_true, y_score, \*[, ...])                                | Compute Area Under the Receiver Operating Characteristic Curve (ROC AUC) from prediction scores. |
| [`metrics.roc_curve`](generated/maxframe.learn.metrics.roc_curve.md#maxframe.learn.metrics.roc_curve)(y_true, y_score[, ...])                                                | Compute Receiver operating characteristic (ROC)                                                  |

## Regression Metrics

| [`metrics.r2_score`](generated/maxframe.learn.metrics.r2_score.md#maxframe.learn.metrics.r2_score)(y_true, y_pred, \*[, ...])   | $R^2$ (coefficient of determination) regression score function.   |
|---------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|

## Pairwise metrics

| [`metrics.pairwise.cosine_distances`](generated/maxframe.learn.metrics.pairwise.cosine_distances.md#maxframe.learn.metrics.pairwise.cosine_distances)(X[, Y])               | Compute cosine distance between samples in X and Y.                                                       |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| [`metrics.pairwise.cosine_similarity`](generated/maxframe.learn.metrics.pairwise.cosine_similarity.md#maxframe.learn.metrics.pairwise.cosine_similarity)(X[, Y, ...])       | Compute cosine similarity between samples in X and Y.                                                     |
| [`metrics.pairwise.euclidean_distances`](generated/maxframe.learn.metrics.pairwise.euclidean_distances.md#maxframe.learn.metrics.pairwise.euclidean_distances)(X[, Y, ...]) | Considering the rows of X (and Y=X) as vectors, compute the distance matrix between each pair of vectors. |
| [`metrics.pairwise.haversine_distances`](generated/maxframe.learn.metrics.pairwise.haversine_distances.md#maxframe.learn.metrics.pairwise.haversine_distances)(X[, Y])      | Compute the Haversine distance between samples in X and Y                                                 |
| [`metrics.pairwise.manhattan_distances`](generated/maxframe.learn.metrics.pairwise.manhattan_distances.md#maxframe.learn.metrics.pairwise.manhattan_distances)(X[, Y])      | Compute the L1 distances between the vectors in X and Y.                                                  |
| [`metrics.pairwise.rbf_kernel`](generated/maxframe.learn.metrics.pairwise.rbf_kernel.md#maxframe.learn.metrics.pairwise.rbf_kernel)(X[, Y, gamma])                          | Compute the rbf (gaussian) kernel between X and Y.                                                        |
| [`metrics.pairwise_distances`](generated/maxframe.learn.metrics.pairwise_distances.md#maxframe.learn.metrics.pairwise_distances)(X[, Y, metric])                            |                                                                                                           |
