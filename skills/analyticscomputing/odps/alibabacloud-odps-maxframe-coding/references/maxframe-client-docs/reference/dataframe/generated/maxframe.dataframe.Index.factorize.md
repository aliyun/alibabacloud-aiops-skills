# maxframe.dataframe.Index.factorize

#### Index.factorize(sort=False, use_na_sentinel=True)

Encode the object as an enumerated type or categorical variable.

This method is useful for obtaining a numeric representation of an
array when all that matters is identifying distinct values. factorize
is available as both a top-level function [`pandas.factorize()`](https://pandas.pydata.org/docs/reference/api/pandas.factorize.html#pandas.factorize),
and as a method [`Series.factorize()`](maxframe.dataframe.Series.factorize.md#maxframe.dataframe.Series.factorize) and [`Index.factorize()`](#maxframe.dataframe.Index.factorize).

* **Parameters:**
  * **values** (*sequence*) – A 1-D sequence. Sequences that aren’t pandas objects are
    coerced to ndarrays before factorization.
  * **sort** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Sort uniques and shuffle codes to maintain the
    relationship.
  * **use_na_sentinel** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If True, the sentinel -1 will be used for NaN values. If False,
    NaN values will be encoded as non-negative integers and will not drop the
    NaN from the uniques of the values.
* **Returns:**
  * **codes** (*ndarray*) – An integer ndarray that’s an indexer into uniques.
    `uniques.take(codes)` will have the same values as values.
  * **uniques** (*ndarray, Index, or Categorical*) – The unique valid values. When values is Categorical, uniques
    is a Categorical. When values is some other pandas object, an
    Index is returned. Otherwise, a 1-D ndarray is returned.

    #### NOTE
    Even if there’s a missing value in values, uniques will
    *not* contain an entry for it.

#### SEE ALSO
`cut`
: Discretize continuous-valued array.

`unique`
: Find the unique value in an array.

### Notes

Reference [the user guide](https://pandas.pydata.org/docs/user_guide/reshaping.html#reshaping-factorize) for more examples.

### Examples

These examples all show factorize as a top-level method like
`pd.factorize(values)`. The results are identical for methods like
[`Series.factorize()`](maxframe.dataframe.Series.factorize.md#maxframe.dataframe.Series.factorize).

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> codes, uniques = md.factorize(mt.array(['b', 'b', 'a', 'c', 'b'], dtype="O"))
>>> codes.execute()
array([0, 0, 1, 2, 0])
>>> uniques.execute()
array(['b', 'a', 'c'], dtype=object)
```

With `sort=True`, the uniques will be sorted, and codes will be
shuffled so that the relationship is the maintained.

```pycon
>>> codes, uniques = md.factorize(mt.array(['b', 'b', 'a', 'c', 'b'], dtype="O"),
...                               sort=True)
>>> codes.execute()
array([1, 1, 0, 2, 1])
>>> uniques.execute()
array(['a', 'b', 'c'], dtype=object)
```

When `use_na_sentinel=True` (the default), missing values are indicated in
the codes with the sentinel value `-1` and missing values are not
included in uniques.

```pycon
>>> codes, uniques = md.factorize(mt.array(['b', None, 'a', 'c', 'b'], dtype="O"))
>>> codes.execute()
array([ 0, -1,  1,  2,  0])
>>> uniques.execute()
array(['b', 'a', 'c'], dtype=object)
```

Thus far, we’ve only factorized lists (which are internally coerced to
NumPy arrays). When factorizing pandas objects, the type of uniques
will differ. For Categoricals, a Categorical is returned.

```pycon
>>> cat = md.Categorical(['a', 'a', 'c'], categories=['a', 'b', 'c'])
>>> codes, uniques = md.factorize(cat)
>>> codes.execute()
array([0, 0, 1])
>>> uniques.execute()
['a', 'c']
Categories (3, object): ['a', 'b', 'c']
```

Notice that `'b'` is in `uniques.categories`, despite not being
present in `cat.values`.

For all other pandas objects, an Index of the appropriate type is
returned.

```pycon
>>> cat = md.Series(['a', 'a', 'c'])
>>> codes, uniques = md.factorize(cat)
>>> codes.execute()
array([0, 0, 1])
>>> uniques.execute()
Index(['a', 'c'], dtype='object')
```

If NaN is in the values, and we want to include NaN in the uniques of the
values, it can be achieved by setting `use_na_sentinel=False`.

```pycon
>>> values = mt.array([1, 2, 1, mt.nan])
>>> codes, uniques = md.factorize(values)  # default: use_na_sentinel=True
>>> codes.execute()
array([ 0,  1,  0, -1])
>>> uniques.execute()
array([1., 2.])
```

```pycon
>>> codes, uniques = md.factorize(values, use_na_sentinel=False)
>>> codes.execute()
array([0, 1, 0, 2])
>>> uniques.execute()
array([ 1.,  2., nan])
```
