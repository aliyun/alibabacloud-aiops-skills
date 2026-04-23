# maxframe.learn.preprocessing.normalize

### maxframe.learn.preprocessing.normalize(X, norm='l2', axis=1, copy=True, return_norm=False)

Scale input vectors individually to unit norm (vector length).

* **Parameters:**
  * **X** ( *{array-like* *,* *sparse matrix}* *,* *shape* *[**n_samples* *,* *n_features* *]*) – The data to normalize, element by element.
    scipy.sparse matrices should be in CSR format to avoid an
    un-necessary copy.
  * **norm** ( *'l1'* *,*  *'l2'* *, or*  *'max'* *,* *optional* *(* *'l2' by default* *)*) – The norm to use to normalize each non zero sample (or each non-zero
    feature if axis is 0).
  * **axis** (*0* *or* *1* *,* *optional* *(**1 by default* *)*) – axis used to normalize the data along. If 1, independently normalize
    each sample, otherwise (if 0) normalize each feature.
  * **copy** (*boolean* *,* *optional* *,* *default True*) – set to False to perform inplace row normalization and avoid a
    copy (if the input is already a tensor and if axis is 1).
  * **return_norm** (*boolean* *,* *default False*) – whether to return the computed norms
* **Returns:**
  * **X** ( *{array-like, sparse matrix}, shape [n_samples, n_features]*) – Normalized input X.
  * **norms** (*Tensor, shape [n_samples] if axis=1 else [n_features]*) – A tensor of norms along given axis for X.
    When X is sparse, a NotImplementedError will be raised
    for norm ‘l1’ or ‘l2’.

#### SEE ALSO
`Normalizer`
: Performs normalization using the `Transformer` API (e.g. as part of a preprocessing `maxframe.learn.pipeline.Pipeline`).
