# maxframe.learn.metrics.auc

### maxframe.learn.metrics.auc(x, y, execute=False, session=None, run_kwargs=None)

Compute Area Under the Curve (AUC) using the trapezoidal rule

This is a general function, given points on a curve.  For computing the
area under the ROC-curve, see [`roc_auc_score()`](maxframe.learn.metrics.roc_auc_score.md#maxframe.learn.metrics.roc_auc_score).  For an alternative
way to summarize a precision-recall curve, see
`average_precision_score()`.

* **Parameters:**
  * **x** (*tensor* *,* *shape =* *[**n* *]*) – x coordinates. These must be either monotonic increasing or monotonic
    decreasing.
  * **y** (*tensor* *,* *shape =* *[**n* *]*) – y coordinates.
* **Returns:**
  **auc**
* **Return type:**
  tensor, with float value

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> from maxframe.learn import metrics
>>> y = mt.array([1, 1, 2, 2])
>>> pred = mt.array([0.1, 0.4, 0.35, 0.8])
>>> fpr, tpr, thresholds = metrics.roc_curve(y, pred, pos_label=2)
>>> metrics.auc(fpr, tpr).execute()
0.75
```

#### SEE ALSO
[`roc_auc_score`](maxframe.learn.metrics.roc_auc_score.md#maxframe.learn.metrics.roc_auc_score)
: Compute the area under the ROC curve

`average_precision_score`
: Compute average precision from prediction scores

`precision_recall_curve`
: Compute precision-recall pairs for different probability thresholds
