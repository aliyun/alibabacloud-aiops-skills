# maxframe.dataframe.DataFrame.dot

#### DataFrame.dot(other)

Compute the matrix multiplication between the DataFrame and other.

This method computes the matrix product between the DataFrame and the
values of an other Series, DataFrame or a numpy array.

It can also be called using `self @ other` in Python >= 3.5.

* **Parameters:**
  **other** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *,* [*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) *or* *array-like*) – The other object to compute the matrix product with.
* **Returns:**
  If other is a Series, return the matrix product between self and
  other as a Series. If other is a DataFrame or a numpy.array, return
  the matrix product of self and other in a DataFrame of a np.array.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
`Series.dot`
: Similar method for Series.

### Notes

The dimensions of DataFrame and other must be compatible in order to
compute the matrix multiplication. In addition, the column names of
DataFrame and the index of other must contain the same values, as they
will be aligned prior to the multiplication.

The dot method for Series computes the inner product, instead of the
matrix product here.

### Examples

Here we multiply a DataFrame with a Series.

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([[0, 1, -2, -1], [1, 1, 1, 1]])
>>> s = md.Series([1, 1, 2, 1])
>>> df.dot(s).execute()
0    -4
1     5
dtype: int64
```

Here we multiply a DataFrame with another DataFrame.

```pycon
>>> other = md.DataFrame([[0, 1], [1, 2], [-1, -1], [2, 0]])
>>> df.dot(other).execute()
    0   1
0   1   4
1   2   2
```

Note that the dot method give the same result as @

```pycon
>>> (df @ other).execute()
    0   1
0   1   4
1   2   2
```

The dot method works also if other is an np.array.

```pycon
>>> arr = mt.array([[0, 1], [1, 2], [-1, -1], [2, 0]])
>>> df.dot(arr).execute()
    0   1
0   1   4
1   2   2
```

Note how shuffling of the objects does not change the result.

```pycon
>>> s2 = s.reindex([1, 0, 2, 3])
>>> df.dot(s2).execute()
0    -4
1     5
dtype: int64
```
