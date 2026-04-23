# maxframe.learn.metrics.accuracy_score

### maxframe.learn.metrics.accuracy_score(y_true, y_pred, normalize=True, sample_weight=None, execute=False, session=None, run_kwargs=None)

Accuracy classification score.

In multilabel classification, this function computes subset accuracy:
the set of labels predicted for a sample must *exactly* match the
corresponding set of labels in y_true.

Read more in the User Guide.

* **Parameters:**
  * **y_true** (*1d array-like* *, or* *label indicator tensor / sparse tensor*) – Ground truth (correct) labels.
  * **y_pred** (*1d array-like* *, or* *label indicator tensor / sparse tensor*) – Predicted labels, as returned by a classifier.
  * **normalize** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional* *(**default=True* *)*) – If `False`, return the number of correctly classified samples.
    Otherwise, return the fraction of correctly classified samples.
  * **sample_weight** (*array-like* *of* *shape* *(**n_samples* *,* *)* *,* *default=None*) – Sample weights.
* **Returns:**
  **score** – If `normalize == True`, return the fraction of correctly
  classified samples (float), else returns the number of correctly
  classified samples (int).

  The best performance is 1 with `normalize == True` and the number
  of samples with `normalize == False`.
* **Return type:**
  [float](https://docs.python.org/3/library/functions.html#float)

#### SEE ALSO
`jaccard_score`, `hamming_loss`, `zero_one_loss`

### Notes

In binary and multiclass classification, this function is equal
to the `jaccard_score` function.

### Examples

```pycon
>>> from maxframe.learn.metrics import accuracy_score
>>> y_pred = [0, 2, 1, 3]
>>> y_true = [0, 1, 2, 3]
>>> accuracy_score(y_true, y_pred).execute()
0.5
>>> accuracy_score(y_true, y_pred, normalize=False).execute()
2
```

In the multilabel case with binary label indicators:

```pycon
>>> import maxframe.tensor as mt
>>> accuracy_score(mt.array([[0, 1], [1, 1]]), mt.ones((2, 2))).execute()
0.5
```
