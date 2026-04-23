# maxframe.learn.metrics.multilabel_confusion_matrix

### maxframe.learn.metrics.multilabel_confusion_matrix(y_true, y_pred, , sample_weight=None, labels=None, samplewise=False, execute=False, session=None, run_kwargs=None)

Compute a confusion matrix for each class or sample.

Compute class-wise (default) or sample-wise (samplewise=True) multilabel
confusion matrix to evaluate the accuracy of a classification, and output
confusion matrices for each class or sample.

In multilabel confusion matrix $MCM$, the count of true negatives
is $MCM_{:,0,0}$, false negatives is $MCM_{:,1,0}$,
true positives is $MCM_{:,1,1}$ and false positives is
$MCM_{:,0,1}$.

Multiclass data will be treated as if binarized under a one-vs-rest
transformation. Returned confusion matrices will be in the order of
sorted unique labels in the union of (y_true, y_pred).

Read more in the User Guide.

* **Parameters:**
  * **y_true** ( *{array-like* *,* *sparse matrix}* *of* *shape* *(**n_samples* *,* *n_outputs* *) or*              *(**n_samples* *,* *)*) – Ground truth (correct) target values.
  * **y_pred** ( *{array-like* *,* *sparse matrix}* *of* *shape* *(**n_samples* *,* *n_outputs* *) or*              *(**n_samples* *,* *)*) – Estimated targets as returned by a classifier.
  * **sample_weight** (*array-like* *of* *shape* *(**n_samples* *,* *)* *,* *default=None*) – Sample weights.
  * **labels** (*array-like* *of* *shape* *(**n_classes* *,* *)* *,* *default=None*) – A list of classes or column indices to select some (or to force
    inclusion of classes absent from the data).
  * **samplewise** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default=False*) – In the multilabel case, this calculates a confusion matrix per sample.
* **Returns:**
  **multi_confusion** – A 2x2 confusion matrix corresponding to each output in the input.
  When calculating class-wise multi_confusion (default), then
  n_outputs = n_labels; when calculating sample-wise multi_confusion
  (samplewise=True), n_outputs = n_samples. If `labels` is defined,
  the results will be returned in the order specified in `labels`,
  otherwise the results will be returned in sorted order by default.
* **Return type:**
  ndarray of shape (n_outputs, 2, 2)

#### SEE ALSO
`confusion_matrix`
: Compute confusion matrix to evaluate the accuracy of a classifier.

### Notes

The multilabel_confusion_matrix calculates class-wise or sample-wise
multilabel confusion matrices, and in multiclass tasks, labels are
binarized under a one-vs-rest way; while
`confusion_matrix()` calculates one confusion matrix
for confusion between every two classes.

### Examples

Multiclass case:

```pycon
>>> import maxframe.tensor as mt
>>> from maxframe.learn.metrics import multilabel_confusion_matrix
>>> y_true = ["cat", "ant", "cat", "cat", "ant", "bird"]
>>> y_pred = ["ant", "ant", "cat", "cat", "ant", "cat"]
>>> multilabel_confusion_matrix(y_true, y_pred,
...                             labels=["ant", "bird", "cat"]).execute()
array([[[3, 1],
        [0, 2]],

       [[5, 0],
        [1, 0]],

       [[2, 1],
        [1, 2]]])
```

Multilabel-indicator case not implemented yet.
