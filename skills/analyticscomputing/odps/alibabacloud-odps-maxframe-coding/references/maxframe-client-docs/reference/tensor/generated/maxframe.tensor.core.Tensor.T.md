# maxframe.tensor.core.Tensor.T

#### *property* Tensor.T

Same as self.transpose(), except that self is returned if
self.ndim < 2.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([[1.,2.],[3.,4.]])
>>> x.execute()
array([[ 1.,  2.],
       [ 3.,  4.]])
>>> x.T.execute()
array([[ 1.,  3.],
       [ 2.,  4.]])
>>> x = mt.array([1.,2.,3.,4.])
>>> x.execute()
array([ 1.,  2.,  3.,  4.])
>>> x.T.execute()
array([ 1.,  2.,  3.,  4.])
```
