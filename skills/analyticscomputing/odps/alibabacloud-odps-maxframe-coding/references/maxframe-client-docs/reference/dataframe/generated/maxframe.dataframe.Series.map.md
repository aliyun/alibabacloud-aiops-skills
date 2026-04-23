# maxframe.dataframe.Series.map

#### Series.map(arg, na_action=None, dtype=None, memory_scale=None, skip_infer=False)

Map values of Series according to input correspondence.

Used for substituting each value in a Series with another value,
that may be derived from a function, a `dict` or
a [`Series`](maxframe.dataframe.Series.md#maxframe.dataframe.Series).

* **Parameters:**
  * **arg** (*function* *,* *collections.abc.Mapping subclass* *or* [*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – Mapping correspondence.
  * **na_action** ( *{None* *,*  *'ignore'}* *,* *default None*) – If ‘ignore’, propagate NaN values, without passing them to the
    mapping correspondence.
  * **dtype** (*np.dtype* *,* *default None*) – Specify return type of the function. Must be specified when
    we cannot decide the return type of the function.
  * **memory_scale** ([*float*](https://docs.python.org/3/library/functions.html#float)) – Specify the scale of memory uses in the function versus
    input size.
  * **skip_infer** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether infer dtypes when dtypes or output_type is not specified
* **Returns:**
  Same index as caller.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Series.apply`](maxframe.dataframe.Series.apply.md#maxframe.dataframe.Series.apply)
: For applying more complex functions on a Series.

[`DataFrame.apply`](maxframe.dataframe.DataFrame.apply.md#maxframe.dataframe.DataFrame.apply)
: Apply a function row-/column-wise.

[`DataFrame.applymap`](maxframe.dataframe.DataFrame.applymap.md#maxframe.dataframe.DataFrame.applymap)
: Apply a function elementwise on a whole DataFrame.

### Notes

When `arg` is a dictionary, values in Series that are not in the
dictionary (as keys) are converted to `NaN`. However, if the
dictionary is a `dict` subclass that defines `__missing__` (i.e.
provides a method for default values), then this default is used
rather than `NaN`.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series(['cat', 'dog', mt.nan, 'rabbit'])
>>> s.execute()
0      cat
1      dog
2      NaN
3   rabbit
dtype: object
```

`map` accepts a `dict` or a `Series`. Values that are not found
in the `dict` are converted to `NaN`, unless the dict has a default
value (e.g. `defaultdict`):

```pycon
>>> s.map({'cat': 'kitten', 'dog': 'puppy'}).execute()
0   kitten
1    puppy
2      NaN
3      NaN
dtype: object
```

It also accepts a function:

```pycon
>>> s.map('I am a {}'.format).execute()
0       I am a cat
1       I am a dog
2       I am a nan
3    I am a rabbit
dtype: object
```

To avoid applying the function to missing values (and keep them as
`NaN`) `na_action='ignore'` can be used:

```pycon
>>> s.map('I am a {}'.format, na_action='ignore').execute()
0     I am a cat
1     I am a dog
2            NaN
3  I am a rabbit
dtype: object
```
