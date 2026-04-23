# maxframe.learn.metrics.f1_score

### maxframe.learn.metrics.f1_score(y_true, y_pred, , labels=None, pos_label=1, average='binary', sample_weight=None, zero_division='warn', execute=False, session=None, run_kwargs=None)

Compute the F1 score, also known as balanced F-score or F-measure

The F1 score can be interpreted as a weighted average of the precision and
recall, where an F1 score reaches its best value at 1 and worst score at 0.
The relative contribution of precision and recall to the F1 score are
equal. The formula for the F1 score is:

```default
F1 = 2 * (precision * recall) / (precision + recall)
```

In the multi-class and multi-label case, this is the average of
the F1 score of each class with weighting depending on the `average`
parameter.

Read more in the User Guide.

* **Parameters:**
  * **y_true** (*1d array-like* *, or* *label indicator array / sparse matrix*) – Ground truth (correct) target values.
  * **y_pred** (*1d array-like* *, or* *label indicator array / sparse matrix*) – Estimated targets as returned by a classifier.
  * **labels** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* *optional*) – The set of labels to include when `average != 'binary'`, and their
    order if `average is None`. Labels present in the data can be
    excluded, for example to calculate a multiclass average ignoring a
    majority negative class, while labels not present in the data will
    result in 0 components in a macro average. For multilabel targets,
    labels are column indices. By default, all labels in `y_true` and
    `y_pred` are used in sorted order.
  * **pos_label** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*int*](https://docs.python.org/3/library/functions.html#int) *,* *1 by default*) – The class to report if `average='binary'` and the data is binary.
    If the data are multiclass or multilabel, this will be ignored;
    setting `labels=[pos_label]` and `average != 'binary'` will report
    scores for that label only.
  * **average** (*string* *,*  *[**None* *,*  *'binary'* *(**default* *)* *,*  *'micro'* *,*  *'macro'* *,*  *'samples'* *,*                         *'weighted'* *]*) – 

    This parameter is required for multiclass/multilabel targets.
    If `None`, the scores for each class are returned. Otherwise, this
    determines the type of averaging performed on the data:

    `'binary'`:
    : Only report results for the class specified by `pos_label`.
      This is applicable only if targets (`y_{true,pred}`) are binary.

    `'micro'`:
    : Calculate metrics globally by counting the total true positives,
      false negatives and false positives.

    `'macro'`:
    : Calculate metrics for each label, and find their unweighted
      mean.  This does not take label imbalance into account.

    `'weighted'`:
    : Calculate metrics for each label, and find their average weighted
      by support (the number of true instances for each label). This
      alters ‘macro’ to account for label imbalance; it can result in an
      F-score that is not between precision and recall.

    `'samples'`:
    : Calculate metrics for each instance, and find their average (only
      meaningful for multilabel classification where this differs from
      [`accuracy_score()`](maxframe.learn.metrics.accuracy_score.md#maxframe.learn.metrics.accuracy_score)).
  * **sample_weight** (*array-like* *of* *shape* *(**n_samples* *,* *)* *,* *default=None*) – Sample weights.
  * **zero_division** ( *"warn"* *,* *0* *or* *1* *,* *default="warn"*) – Sets the value to return when there is a zero division, i.e. when all
    predictions and labels are negative. If set to “warn”, this acts as 0,
    but warnings are also raised.
* **Returns:**
  **f1_score** – F1 score of the positive class in binary classification or weighted
  average of the F1 scores of each class for the multiclass task.
* **Return type:**
  [float](https://docs.python.org/3/library/functions.html#float) or array of [float](https://docs.python.org/3/library/functions.html#float), shape = [n_unique_labels]

#### SEE ALSO
[`fbeta_score`](maxframe.learn.metrics.fbeta_score.md#maxframe.learn.metrics.fbeta_score), [`precision_recall_fscore_support`](maxframe.learn.metrics.precision_recall_fscore_support.md#maxframe.learn.metrics.precision_recall_fscore_support), `jaccard_score`, [`multilabel_confusion_matrix`](maxframe.learn.metrics.multilabel_confusion_matrix.md#maxframe.learn.metrics.multilabel_confusion_matrix)

### References

* <a id='id1'>**[1]**</a> [Wikipedia entry for the F1-score](https://en.wikipedia.org/wiki/F1_score)

### Examples

```pycon
>>> from maxframe.learn.metrics import f1_score
>>> y_true = [0, 1, 2, 0, 1, 2]
>>> y_pred = [0, 2, 1, 0, 0, 1]
>>> f1_score(y_true, y_pred, average='macro')
0.26...
>>> f1_score(y_true, y_pred, average='micro')
0.33...
>>> f1_score(y_true, y_pred, average='weighted')
0.26...
>>> f1_score(y_true, y_pred, average=None)
array([0.8, 0. , 0. ])
>>> y_true = [0, 0, 0, 0, 0, 0]
>>> y_pred = [0, 0, 0, 0, 0, 0]
>>> f1_score(y_true, y_pred, zero_division=1)
1.0...
```

### Notes

When `true positive + false positive == 0`, precision is undefined;
When `true positive + false negative == 0`, recall is undefined.
In such cases, by default the metric will be set to 0, as will f-score,
and `UndefinedMetricWarning` will be raised. This behavior can be
modified with `zero_division`.
