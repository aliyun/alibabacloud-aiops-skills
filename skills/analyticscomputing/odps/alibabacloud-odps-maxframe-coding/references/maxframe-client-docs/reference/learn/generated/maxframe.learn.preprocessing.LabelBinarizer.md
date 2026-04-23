# maxframe.learn.preprocessing.LabelBinarizer

### *class* maxframe.learn.preprocessing.LabelBinarizer(, neg_label=0, pos_label=1, sparse_output=False)

Binarize labels in a one-vs-all fashion.

Several regression and binary classification algorithms are
available in scikit-learn. A simple way to extend these algorithms
to the multi-class classification case is to use the so-called
one-vs-all scheme.

At learning time, this simply consists in learning one regressor
or binary classifier per class. In doing so, one needs to convert
multi-class labels to binary labels (belong or does not belong
to the class). LabelBinarizer makes this process easy with the
transform method.

At prediction time, one assigns the class for which the corresponding
model gave the greatest confidence. LabelBinarizer makes this easy
with the inverse_transform method.

Read more in the User Guide.

* **Parameters:**
  * **neg_label** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default=0*) – Value with which negative labels must be encoded.
  * **pos_label** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default=1*) – Value with which positive labels must be encoded.
  * **sparse_output** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default=False*) – True if the returned array from transform is desired to be in sparse
    CSR format.

#### classes_

Holds the label for each class.

* **Type:**
  ndarray of shape (n_classes,)

#### y_type_

Represents the type of the target data as evaluated by
utils.multiclass.type_of_target. Possible type are ‘continuous’,
‘continuous-multioutput’, ‘binary’, ‘multiclass’,
‘multiclass-multioutput’, ‘multilabel-indicator’, and ‘unknown’.

* **Type:**
  [str](https://docs.python.org/3/library/stdtypes.html#str)

#### sparse_input_

True if the input data to transform is given as a sparse matrix, False
otherwise.

* **Type:**
  [bool](https://docs.python.org/3/library/functions.html#bool)

### Examples

```pycon
>>> from maxframe.learn import preprocessing
>>> lb = preprocessing.LabelBinarizer()
>>> lb.fit([1, 2, 6, 4, 2])
LabelBinarizer()
>>> lb.classes_.execute()
array([1, 2, 4, 6])
>>> lb.transform([1, 6]).execute()
array([[1, 0, 0, 0],
       [0, 0, 0, 1]])
```

Binary targets transform to a column vector

```pycon
>>> lb = preprocessing.LabelBinarizer()
>>> lb.fit_transform(['yes', 'no', 'no', 'yes']).execute()
array([[1],
       [0],
       [0],
       [1]])
```

Passing a 2D matrix for multilabel classification

```pycon
>>> import numpy as np
>>> lb.fit(np.array([[0, 1, 1], [1, 0, 0]]))
LabelBinarizer()
>>> lb.classes_.execute()
array([0, 1, 2])
>>> lb.transform([0, 1, 2, 1]).execute()
array([[1, 0, 0],
       [0, 1, 0],
       [0, 0, 1],
       [0, 1, 0]])
```

#### SEE ALSO
[`label_binarize`](maxframe.learn.preprocessing.label_binarize.md#maxframe.learn.preprocessing.label_binarize)
: Function to perform the transform operation of LabelBinarizer with fixed classes.

`OneHotEncoder`
: Encode categorical features using a one-hot aka one-of-K scheme.

#### \_\_init_\_(, neg_label=0, pos_label=1, sparse_output=False)

### Methods

| [`__init__`](#maxframe.learn.preprocessing.LabelBinarizer.__init__)(\*[, neg_label, pos_label, ...])   |                                                                        |
|--------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| `execute`([session, run_kwargs, extra_tileables])                                                      |                                                                        |
| `fetch`([session, run_kwargs])                                                                         |                                                                        |
| `fit`(y[, check, execute, session, run_kwargs])                                                        | Fit label binarizer.                                                   |
| `fit_transform`(y[, check, execute, session, ...])                                                     | Fit label binarizer and transform multi-class labels to binary labels. |
| `get_metadata_routing`()                                                                               | Get metadata routing of this object.                                   |
| `get_params`([deep])                                                                                   | Get parameters for this estimator.                                     |
| `inverse_transform`(Y[, threshold])                                                                    | Transform binary labels back to multi-class labels.                    |
| `set_fit_request`(\*[, check, execute, ...])                                                           | Request metadata passed to the `fit` method.                           |
| `set_inverse_transform_request`(\*[, threshold])                                                       | Request metadata passed to the `inverse_transform` method.             |
| `set_params`(\*\*params)                                                                               | Set the parameters of this estimator.                                  |
| `set_transform_request`(\*[, check, execute, ...])                                                     | Request metadata passed to the `transform` method.                     |
| `transform`(y[, check, execute, session, ...])                                                         | Transform multi-class labels to binary labels.                         |
