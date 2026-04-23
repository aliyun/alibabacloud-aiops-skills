# maxframe.learn.model_selection.train_test_split

### maxframe.learn.model_selection.train_test_split(\*arrays, \*\*options)

Split arrays or matrices into random train and test subsets

* **Parameters:**
  * **\*arrays** (*sequence* *of* *indexables with same length / shape* *[**0* *]*) – Allowed inputs are lists, numpy arrays, scipy-sparse
    matrices or pandas dataframes.
  * **test_size** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* [*int*](https://docs.python.org/3/library/functions.html#int) *or* *None* *,* *optional* *(**default=None* *)*) – If float, should be between 0.0 and 1.0 and represent the proportion
    of the dataset to include in the test split. If int, represents the
    absolute number of test samples. If None, the value is set to the
    complement of the train size. If `train_size` is also None, it will
    be set to 0.25.
  * **train_size** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* [*int*](https://docs.python.org/3/library/functions.html#int) *, or* *None* *,*  *(**default=None* *)*) – If float, should be between 0.0 and 1.0 and represent the
    proportion of the dataset to include in the train split. If
    int, represents the absolute number of train samples. If None,
    the value is automatically set to the complement of the test size.
  * **random_state** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *RandomState instance* *or* *None* *,* *optional* *(**default=None* *)*) – If int, random_state is the seed used by the random number generator;
    If RandomState instance, random_state is the random number generator;
    If None, the random number generator is the RandomState instance used
    by np.random.
  * **shuffle** (*boolean* *,* *optional* *(**default=True* *)*) – Whether or not to shuffle the data before splitting. If shuffle=False
    then stratify must be None. CURRENTLY only shuffle=False is supported.
  * **stratify** (*array-like* *or* *None* *(**default=None* *)*) – If not None, data is split in a stratified fashion, using this as
    the class labels.
* **Returns:**
  **splitting** – List containing train-test split of inputs.
* **Return type:**
  [list](https://docs.python.org/3/library/stdtypes.html#list), length=2 \* len(arrays)

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> from maxframe.learn.model_selection import train_test_split
>>> X, y = mt.arange(10).reshape((5, 2)), range(5)
>>> X.execute()
array([[0, 1],
       [2, 3],
       [4, 5],
       [6, 7],
       [8, 9]])
>>> list(y)
[0, 1, 2, 3, 4]
```

```pycon
>>> X_train, X_test, y_train, y_test = train_test_split(
...     X, y, test_size=0.33, random_state=42)
...
>>> X_train.execute()
array([[8, 9],
       [0, 1],
       [4, 5]])
>>> y_train.execute()
array([4, 0, 2])
>>> X_test.execute()
array([[2, 3],
       [6, 7]])
>>> y_test.execute()
array([1, 3])
```

```pycon
>>> train_test_split(y, shuffle=False)
[array([0, 1, 2]), array([3, 4])]
```
