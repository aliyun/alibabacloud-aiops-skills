# maxframe.dataframe.Series.to_dict

#### Series.to_dict(into=<class 'dict'>, batch_size=10000, session=None)

Convert Series to {label -> value} dict or dict-like object.

* **Parameters:**
  **into** (*class* *,* *default dict*) – The collections.abc.Mapping subclass to use as the return
  object. Can be the actual class or an empty
  instance of the mapping type you want.  If you want a
  collections.defaultdict, you must pass it initialized.
* **Returns:**
  Key-value representation of Series.
* **Return type:**
  [collections.abc.Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series([1, 2, 3, 4])
>>> s.to_dict()
{0: 1, 1: 2, 2: 3, 3: 4}
>>> from collections import OrderedDict, defaultdict
>>> s.to_dict(OrderedDict)
OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
>>> dd = defaultdict(list)
>>> s.to_dict(dd)
defaultdict(<class 'list'>, {0: 1, 1: 2, 2: 3, 3: 4})
```
