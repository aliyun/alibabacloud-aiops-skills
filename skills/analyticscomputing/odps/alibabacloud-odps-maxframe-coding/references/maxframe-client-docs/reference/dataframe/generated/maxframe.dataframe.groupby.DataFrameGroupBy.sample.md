# maxframe.dataframe.groupby.DataFrameGroupBy.sample

#### DataFrameGroupBy.sample(n: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, frac: [float](https://docs.python.org/3/library/functions.html#float) | [None](https://docs.python.org/3/library/constants.html#None) = None, replace: [bool](https://docs.python.org/3/library/functions.html#bool) = False, weights: [Sequence](https://docs.python.org/3/library/typing.html#typing.Sequence) | Series | [None](https://docs.python.org/3/library/constants.html#None) = None, random_state: [RandomState](https://numpy.org/doc/stable/reference/random/legacy.html#numpy.random.RandomState) | [None](https://docs.python.org/3/library/constants.html#None) = None, errors: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'ignore')

Return a random sample of items from each group.

You can use random_state for reproducibility.

* **Parameters:**
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Number of items to return for each group. Cannot be used with
    frac and must be no larger than the smallest group unless
    replace is True. Default is one if frac is None.
  * **frac** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional*) – Fraction of items to return. Cannot be used with n.
  * **replace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Allow or disallow sampling of the same row more than once.
  * **weights** (*list-like* *,* *optional*) – Default None results in equal probability weighting.
    If passed a list-like then values must have the same length as
    the underlying DataFrame or Series object and will be used as
    sampling probabilities after normalization within each group.
    Values must be non-negative with at least one positive element
    within each group.
  * **random_state** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *array-like* *,* *BitGenerator* *,* *np.random.RandomState* *,* *optional*) – If int, array-like, or BitGenerator (NumPy>=1.17), seed for
    random number generator
    If np.random.RandomState, use as numpy RandomState object.
  * **errors** ( *{'ignore'* *,*  *'raise'}* *,* *default 'ignore'*) – If ignore, errors will not be raised when replace is False
    and size of some group is less than n.
* **Returns:**
  A new object of same type as caller containing items randomly
  sampled within each group from the caller object.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
`DataFrame.sample`
: Generate random samples from a DataFrame object.

[`numpy.random.choice`](https://numpy.org/doc/stable/reference/random/generated/numpy.random.choice.html#numpy.random.choice)
: Generate a random sample from a given 1-D numpy array.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame(
...     {"a": ["red"] * 2 + ["blue"] * 2 + ["black"] * 2, "b": range(6)}
... )
>>> df.execute()
       a  b
0    red  0
1    red  1
2   blue  2
3   blue  3
4  black  4
5  black  5
```

Select one row at random for each distinct value in column a. The
random_state argument can be used to guarantee reproducibility:

```pycon
>>> df.groupby("a").sample(n=1, random_state=1).execute()
       a  b
4  black  4
2   blue  2
1    red  1
```

Set frac to sample fixed proportions rather than counts:

```pycon
>>> df.groupby("a")["b"].sample(frac=0.5, random_state=2).execute()
5    5
2    2
0    0
Name: b, dtype: int64
```

Control sample probabilities within groups by setting weights:

```pycon
>>> df.groupby("a").sample(
...     n=1,
...     weights=[1, 1, 1, 0, 0, 1],
...     random_state=1,
... ).execute()
       a  b
5  black  5
2   blue  2
0    red  0
```
