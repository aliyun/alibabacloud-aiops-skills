# maxframe.dataframe.Index.rename

#### Index.rename(name, inplace=False)

Alter Index or MultiIndex name.

Able to set new names without level. Defaults to returning new index.
Length of names must match number of levels in MultiIndex.

* **Parameters:**
  * **name** (*label* *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *labels*) – Name(s) to set.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Modifies the object directly, instead of creating a new Index or
    MultiIndex.
* **Returns:**
  The same type as the caller or None if inplace is True.
* **Return type:**
  [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

#### SEE ALSO
[`Index.set_names`](maxframe.dataframe.Index.set_names.md#maxframe.dataframe.Index.set_names)
: Able to set new names partially and by level.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> idx = md.Index(['A', 'C', 'A', 'B'], name='score')
>>> idx.rename('grade').execute()
Index(['A', 'C', 'A', 'B'], dtype='object', name='grade')
```

```pycon
>>> idx = md.Index([('python', 2018),
...                 ('python', 2019),
...                 ('cobra', 2018),
...                 ('cobra', 2019)],
...                names=['kind', 'year'])
>>> idx.execute()
MultiIndex([('python', 2018),
            ('python', 2019),
            ( 'cobra', 2018),
            ( 'cobra', 2019)],
           names=['kind', 'year'])
>>> idx.rename(['species', 'year']).execute()
MultiIndex([('python', 2018),
            ('python', 2019),
            ( 'cobra', 2018),
            ( 'cobra', 2019)],
           names=['species', 'year'])
>>> idx.rename('species').execute()
Traceback (most recent call last):
TypeError: Must pass list-like as `names`.
```
