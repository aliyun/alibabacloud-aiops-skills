# maxframe.dataframe.DataFrame.sample

#### DataFrame.sample(n=None, frac=None, replace=False, weights=None, random_state=None, axis=None, always_multinomial=False)

Return a random sample of items from an axis of object.

You can use random_state for reproducibility.

* **Parameters:**
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Number of items from axis to return. Cannot be used with frac.
    Default = 1 if frac = None.
  * **frac** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional*) – Fraction of axis items to return. Cannot be used with n.
  * **replace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Allow or disallow sampling of the same row more than once.
  * **weights** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *ndarray-like* *,* *optional*) – Default ‘None’ results in equal probability weighting.
    If passed a Series, will align with target object on index. Index
    values in weights not found in sampled object will be ignored and
    index values in sampled object not in weights will be assigned
    weights of zero.
    If called on a DataFrame, will accept the name of a column
    when axis = 0.
    Unless weights are a Series, weights must be same length as axis
    being sampled.
    If weights do not sum to 1, they will be normalized to sum to 1.
    Missing values in the weights column will be treated as zero.
    Infinite values not allowed.
  * **random_state** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *array-like* *,* *BitGenerator* *,* *np.random.RandomState* *,* *optional*) – If int, array-like, or BitGenerator (NumPy>=1.17), seed for
    random number generator
    If np.random.RandomState, use as numpy RandomState object.
  * **axis** ( *{0* *or*  *‘index’* *,* *1* *or*  *‘columns’* *,* *None}* *,* *default None*) – Axis to sample. Accepts axis number or name. Default is stat axis
    for given data type (0 for Series and DataFrames).
  * **always_multinomial** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, always treat distribution of sample counts between data chunks
    as multinomial distribution. This will accelerate sampling when data
    is huge, but may affect randomness of samples when number of instances
    is not very large.
* **Returns:**
  A new object of same type as caller containing n items randomly
  sampled from the caller object.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
`DataFrameGroupBy.sample`
: Generates random samples from each group of a DataFrame object.

`SeriesGroupBy.sample`
: Generates random samples from each group of a Series object.

[`numpy.random.choice`](https://numpy.org/doc/stable/reference/random/generated/numpy.random.choice.html#numpy.random.choice)
: Generates a random sample from a given 1-D numpy array.

### Notes

If frac > 1, replacement should be set to True.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'num_legs': [2, 4, 8, 0],
...                    'num_wings': [2, 0, 0, 0],
...                    'num_specimen_seen': [10, 2, 1, 8]},
...                   index=['falcon', 'dog', 'spider', 'fish'])
>>> df.execute()
        num_legs  num_wings  num_specimen_seen
falcon         2          2                 10
dog            4          0                  2
spider         8          0                  1
fish           0          0                  8
```

Extract 3 random elements from the `Series` `df['num_legs']`:
Note that we use random_state to ensure the reproducibility of
the examples.

```pycon
>>> df['num_legs'].sample(n=3, random_state=1).execute()
fish      0
spider    8
falcon    2
Name: num_legs, dtype: int64
```

A random 50% sample of the `DataFrame` with replacement:

```pycon
>>> df.sample(frac=0.5, replace=True, random_state=1).execute()
      num_legs  num_wings  num_specimen_seen
dog          4          0                  2
fish         0          0                  8
```

An upsample sample of the `DataFrame` with replacement:
Note that replace parameter has to be True for frac parameter > 1.

```pycon
>>> df.sample(frac=2, replace=True, random_state=1).execute()
        num_legs  num_wings  num_specimen_seen
dog            4          0                  2
fish           0          0                  8
falcon         2          2                 10
falcon         2          2                 10
fish           0          0                  8
dog            4          0                  2
fish           0          0                  8
dog            4          0                  2
```

Using a DataFrame column as weights. Rows with larger value in the
num_specimen_seen column are more likely to be sampled.

```pycon
>>> df.sample(n=2, weights='num_specimen_seen', random_state=1).execute()
        num_legs  num_wings  num_specimen_seen
falcon         2          2                 10
fish           0          0                  8
```
