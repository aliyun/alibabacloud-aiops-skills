# maxframe.learn.model_selection.KFold

### *class* maxframe.learn.model_selection.KFold(n_splits=5, , shuffle=False, random_state=None)

K-Folds cross-validator

Provides train/test indices to split data in train/test sets. Split
dataset into k consecutive folds (without shuffling by default).

Each fold is then used once as a validation while the k - 1 remaining
folds form the training set.

* **Parameters:**
  * **n_splits** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default=5*) – 

    Number of folds. Must be at least 2.

    #### Versionchanged
    Changed in version 0.22: `n_splits` default value changed from 3 to 5.
  * **shuffle** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default=False*) – Whether to shuffle the data before splitting into batches.
    Note that the samples within each split will not be shuffled.
  * **random_state** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *RandomState instance* *or* *None* *,* *default=None*) – When shuffle is True, random_state affects the ordering of the
    indices, which controls the randomness of each fold. Otherwise, this
    parameter has no effect.
    Pass an int for reproducible output across multiple function calls.
    See Glossary.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> from maxframe.learn.model_selection import KFold
>>> X = mt.array([[1, 2], [3, 4], [1, 2], [3, 4]])
>>> y = mt.array([1, 2, 3, 4])
>>> kf = KFold(n_splits=2)
>>> kf.get_n_splits(X)
2
>>> print(kf)
KFold(n_splits=2, random_state=None, shuffle=False)
>>> for train_index, test_index in kf.split(X):
...     print("TRAIN:", train_index, "TEST:", test_index)
...     X_train, X_test = X[train_index], X[test_index]
...     y_train, y_test = y[train_index], y[test_index]
TRAIN: [2 3] TEST: [0 1]
TRAIN: [0 1] TEST: [2 3]
```

### Notes

The first `n_samples % n_splits` folds have size
`n_samples // n_splits + 1`, other folds have size
`n_samples // n_splits`, where `n_samples` is the number of samples.

Randomized CV splitters may return different results for each call of
split. You can make the results identical by setting random_state
to an integer.

#### SEE ALSO
`StratifiedKFold`
: Takes group information into account to avoid building folds with imbalanced class distributions (for binary or multiclass classification tasks).

`GroupKFold`
: K-fold iterator variant with non-overlapping groups.

`RepeatedKFold`
: Repeats K-Fold n times.

#### \_\_init_\_(n_splits=5, , shuffle=False, random_state=None)

### Methods

| [`__init__`](#maxframe.learn.model_selection.KFold.__init__)([n_splits, shuffle, random_state])   |                                                                   |
|---------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| `get_n_splits`([X, y, groups])                                                                    | Returns the number of splitting iterations in the cross-validator |
| `split`(X[, y, groups])                                                                           | Generate indices to split data into training and test set.        |
