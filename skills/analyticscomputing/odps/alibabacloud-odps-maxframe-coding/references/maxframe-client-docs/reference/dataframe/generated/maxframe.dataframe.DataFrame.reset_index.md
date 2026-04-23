# maxframe.dataframe.DataFrame.reset_index

#### DataFrame.reset_index(level=None, drop=False, inplace=False, col_level=0, col_fill='', names=None, default_index_type: DefaultIndexType | [str](https://docs.python.org/3/library/stdtypes.html#str) = None, \*\*kwargs)

Reset the index, or a level of it.

Reset the index of the DataFrame, and use the default one instead.
If the DataFrame has a MultiIndex, this method can remove one or more
levels.

* **Parameters:**
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *, or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* *default None*) – Only remove the given levels from the index. Removes all levels by
    default.
  * **drop** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Do not try to insert index into dataframe columns. This resets
    the index to the default integer index.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Modify the DataFrame in place (do not create a new object).
  * **col_level** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default 0*) – If the columns have multiple levels, determines which level the
    labels are inserted into. By default it is inserted into the first
    level.
  * **col_fill** ([*object*](https://docs.python.org/3/library/functions.html#object) *,* *default ''*) – If the columns have multiple levels, determines how the other
    levels are named. If None then the index name is repeated.
* **Returns:**
  DataFrame with the new index or None if `inplace=True`.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) or None

#### SEE ALSO
[`DataFrame.set_index`](maxframe.dataframe.DataFrame.set_index.md#maxframe.dataframe.DataFrame.set_index)
: Opposite of reset_index.

[`DataFrame.reindex`](maxframe.dataframe.DataFrame.reindex.md#maxframe.dataframe.DataFrame.reindex)
: Change to new indices or expand indices.

[`DataFrame.reindex_like`](maxframe.dataframe.DataFrame.reindex_like.md#maxframe.dataframe.DataFrame.reindex_like)
: Change to same indices as other DataFrame.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([('bird', 389.0),
...                    ('bird', 24.0),
...                    ('mammal', 80.5),
...                    ('mammal', mt.nan)],
...                   index=['falcon', 'parrot', 'lion', 'monkey'],
...                   columns=('class', 'max_speed'))
>>> df.execute()
         class  max_speed
falcon    bird      389.0
parrot    bird       24.0
lion    mammal       80.5
monkey  mammal        NaN
```

When we reset the index, the old index is added as a column, and a
new sequential index is used:

```pycon
>>> df.reset_index().execute()
    index   class  max_speed
0  falcon    bird      389.0
1  parrot    bird       24.0
2    lion  mammal       80.5
3  monkey  mammal        NaN
```

We can use the drop parameter to avoid the old index being added as
a column:

```pycon
>>> df.reset_index(drop=True).execute()
    class  max_speed
0    bird      389.0
1    bird       24.0
2  mammal       80.5
3  mammal        NaN
```

You can also use reset_index with MultiIndex.

```pycon
>>> import pandas as pd
>>> index = pd.MultiIndex.from_tuples([('bird', 'falcon'),
...                                    ('bird', 'parrot'),
...                                    ('mammal', 'lion'),
...                                    ('mammal', 'monkey')],
...                                   names=['class', 'name'])
>>> columns = pd.MultiIndex.from_tuples([('speed', 'max'),
...                                      ('species', 'type')])
>>> df = md.DataFrame([(389.0, 'fly'),
...                    ( 24.0, 'fly'),
...                    ( 80.5, 'run'),
...                    (mt.nan, 'jump')],
...                   index=index,
...                   columns=columns)
>>> df.execute()
               speed species
                 max    type
class  name
bird   falcon  389.0     fly
       parrot   24.0     fly
mammal lion     80.5     run
       monkey    NaN    jump
```

If the index has multiple levels, we can reset a subset of them:

```pycon
>>> df.reset_index(level='class').execute()
         class  speed species
                  max    type
name
falcon    bird  389.0     fly
parrot    bird   24.0     fly
lion    mammal   80.5     run
monkey  mammal    NaN    jump
```

If we are not dropping the index, by default, it is placed in the top
level. We can place it in another level:

```pycon
>>> df.reset_index(level='class', col_level=1).execute()
                speed species
         class    max    type
name
falcon    bird  389.0     fly
parrot    bird   24.0     fly
lion    mammal   80.5     run
monkey  mammal    NaN    jump
```

When the index is inserted under another level, we can specify under
which one with the parameter col_fill:

```pycon
>>> df.reset_index(level='class', col_level=1, col_fill='species').execute()
              species  speed species
                class    max    type
name
falcon           bird  389.0     fly
parrot           bird   24.0     fly
lion           mammal   80.5     run
monkey         mammal    NaN    jump
```

If we specify a nonexistent level for col_fill, it is created:

```pycon
>>> df.reset_index(level='class', col_level=1, col_fill='genus').execute()
                genus  speed species
                class    max    type
name
falcon           bird  389.0     fly
parrot           bird   24.0     fly
lion           mammal   80.5     run
monkey         mammal    NaN    jump
```
