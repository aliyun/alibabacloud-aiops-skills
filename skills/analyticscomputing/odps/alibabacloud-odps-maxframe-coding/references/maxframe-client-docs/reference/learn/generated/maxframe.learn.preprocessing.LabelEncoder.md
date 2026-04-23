# maxframe.learn.preprocessing.LabelEncoder

### *class* maxframe.learn.preprocessing.LabelEncoder

Encode target labels with value between 0 and n_classes-1.

This transformer should be used to encode target values, *i.e.* y, and
not the input X.

Read more in the User Guide.

#### classes_

Holds the label for each class.

* **Type:**
  ndarray of shape (n_classes,)

#### SEE ALSO
`OrdinalEncoder`
: Encode categorical features using an ordinal encoding scheme.

`OneHotEncoder`
: Encode categorical features as a one-hot numeric array.

### Examples

LabelEncoder can be used to normalize labels.

```pycon
>>> from maxframe.learn import preprocessing
>>> le = preprocessing.LabelEncoder()
>>> le.fit([1, 2, 2, 6]).execute()
LabelEncoder()
>>> le.classes_.to_numpy()
array([1, 2, 6])
>>> le.transform([1, 1, 2, 6]).to_numpy()
array([0, 0, 1, 2]...)
>>> le.inverse_transform([0, 0, 1, 2]).to_numpy()
array([1, 1, 2, 6])
```

It can also be used to transform non-numerical labels (as long as they are
hashable and comparable) to numerical labels.

```pycon
>>> le = preprocessing.LabelEncoder()
>>> le.fit(["paris", "paris", "tokyo", "amsterdam"]).execute()
LabelEncoder()
>>> list(le.classes_.to_numpy())
['amsterdam', 'paris', 'tokyo']
>>> le.transform(["tokyo", "tokyo", "paris"]).to_numpy()
array([2, 2, 1]...)
>>> list(le.inverse_transform([2, 2, 1]).to_numpy())
['tokyo', 'tokyo', 'paris']
```

#### \_\_init_\_()

### Methods

| [`__init__`](#maxframe.learn.preprocessing.LabelEncoder.__init__)()   |                                                            |
|-----------------------------------------------------------------------|------------------------------------------------------------|
| `execute`([session, run_kwargs, extra_tileables])                     |                                                            |
| `fetch`([session, run_kwargs])                                        |                                                            |
| `fit`(y[, execute, session, run_kwargs])                              | Fit label encoder.                                         |
| `fit_transform`(y[, execute, session, run_kwargs])                    | Fit label encoder and return encoded labels.               |
| `get_metadata_routing`()                                              | Get metadata routing of this object.                       |
| `get_params`([deep])                                                  | Get parameters for this estimator.                         |
| `inverse_transform`(y[, execute, session, ...])                       | Transform labels back to original encoding.                |
| `set_fit_request`(\*[, execute, run_kwargs, ...])                     | Request metadata passed to the `fit` method.               |
| `set_inverse_transform_request`(\*[, execute, ...])                   | Request metadata passed to the `inverse_transform` method. |
| `set_params`(\*\*params)                                              | Set the parameters of this estimator.                      |
| `set_transform_request`(\*[, execute, ...])                           | Request metadata passed to the `transform` method.         |
| `transform`(y[, execute, session, run_kwargs])                        | Transform labels to normalized encoding.                   |
