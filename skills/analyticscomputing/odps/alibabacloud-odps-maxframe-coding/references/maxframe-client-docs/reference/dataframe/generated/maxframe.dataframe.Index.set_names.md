# maxframe.dataframe.Index.set_names

#### Index.set_names(names, level=None, inplace=False)

Set Index or MultiIndex name.

Able to set new names partially and by level.

* **Parameters:**
  * **names** (*label* *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *label*) – Name(s) to set.
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *label* *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* *label* *,* *optional*) – If the index is a MultiIndex, level(s) to set (None for all
    levels). Otherwise level must be None.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Modifies the object directly, instead of creating a new Index or
    MultiIndex.
* **Returns:**
  The same type as the caller or None if inplace is True.
* **Return type:**
  [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

#### SEE ALSO
[`Index.rename`](maxframe.dataframe.Index.rename.md#maxframe.dataframe.Index.rename)
: Able to set new names without level.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> idx = md.Index([1, 2, 3, 4])
>>> idx.execute()
Int64Index([1, 2, 3, 4], dtype='int64')
>>> idx.set_names('quarter').execute()
Int64Index([1, 2, 3, 4], dtype='int64', name='quarter')
```
