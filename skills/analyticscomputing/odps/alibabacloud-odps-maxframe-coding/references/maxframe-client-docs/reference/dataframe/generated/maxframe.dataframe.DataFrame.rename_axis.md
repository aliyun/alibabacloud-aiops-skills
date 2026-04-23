# maxframe.dataframe.DataFrame.rename_axis

#### DataFrame.rename_axis(mapper=<no_default>, index=<no_default>, columns=<no_default>, axis=0, copy=True, inplace=False)

Set the name of the axis for the index or columns.

* **Parameters:**
  * **mapper** (*scalar* *,* *list-like* *,* *optional*) – Value to set the axis name attribute.
  * **index** (*scalar* *,* *list-like* *,* *dict-like* *or* *function* *,* *optional*) – 

    A scalar, list-like, dict-like or functions transformations to
    apply to that axis’ values.
    Note that the `columns` parameter is not allowed if the
    object is a Series. This parameter only apply for DataFrame
    type objects.

    Use either `mapper` and `axis` to
    specify the axis to target with `mapper`, or `index`
    and/or `columns`.
  * **columns** (*scalar* *,* *list-like* *,* *dict-like* *or* *function* *,* *optional*) – 

    A scalar, list-like, dict-like or functions transformations to
    apply to that axis’ values.
    Note that the `columns` parameter is not allowed if the
    object is a Series. This parameter only apply for DataFrame
    type objects.

    Use either `mapper` and `axis` to
    specify the axis to target with `mapper`, or `index`
    and/or `columns`.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – The axis to rename.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Also copy underlying data.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Modifies the object directly, instead of creating a new Series
    or DataFrame.
* **Returns:**
  The same type as the caller or None if inplace is True.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series), [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame), or None

#### SEE ALSO
[`Series.rename`](maxframe.dataframe.Series.rename.md#maxframe.dataframe.Series.rename)
: Alter Series index labels or name.

[`DataFrame.rename`](maxframe.dataframe.DataFrame.rename.md#maxframe.dataframe.DataFrame.rename)
: Alter DataFrame index labels or name.

[`Index.rename`](maxframe.dataframe.Index.rename.md#maxframe.dataframe.Index.rename)
: Set new names on index.

### Notes

`DataFrame.rename_axis` supports two calling conventions

* `(index=index_mapper, columns=columns_mapper, ...)`
* `(mapper, axis={'index', 'columns'}, ...)`

The first calling convention will only modify the names of
the index and/or the names of the Index object that is the columns.
In this case, the parameter `copy` is ignored.

The second calling convention will modify the names of the
the corresponding index if mapper is a list or a scalar.
However, if mapper is dict-like or a function, it will use the
deprecated behavior of modifying the axis *labels*.

We *highly* recommend using keyword arguments to clarify your
intent.

### Examples

**Series**

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(["dog", "cat", "monkey"])
>>> s.execute()
0       dog
1       cat
2    monkey
dtype: object
>>> s.rename_axis("animal").execute()
animal
0    dog
1    cat
2    monkey
dtype: object
```

**DataFrame**

```pycon
>>> df = md.DataFrame({"num_legs": [4, 4, 2],
...                    "num_arms": [0, 0, 2]},
...                   ["dog", "cat", "monkey"])
>>> df.execute()
        num_legs  num_arms
dog            4         0
cat            4         0
monkey         2         2
>>> df = df.rename_axis("animal")
>>> df.execute()
        num_legs  num_arms
animal
dog            4         0
cat            4         0
monkey         2         2
>>> df = df.rename_axis("limbs", axis="columns")
>>> df.execute()
limbs   num_legs  num_arms
animal
dog            4         0
cat            4         0
monkey         2         2
```
