# maxframe.dataframe.DataFrame.combine_first

#### DataFrame.combine_first(other)

Update null elements with value in the same location in other.

Combine two DataFrame objects by filling null values in one DataFrame
with non-null values from other DataFrame. The row and column indexes
of the resulting DataFrame will be the union of the two. The resulting
dataframe contains the ‘first’ dataframe values and overrides the
second one values where both first.loc[index, col] and
second.loc[index, col] are not missing values, upon calling
first.combine_first(second).

* **Parameters:**
  **other** ([*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)) – Provided DataFrame to use to fill null values.
* **Returns:**
  The result of combining the provided DataFrame with the other object.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.combine`](maxframe.dataframe.DataFrame.combine.md#maxframe.dataframe.DataFrame.combine)
: Perform series-wise operation on two DataFrames using a given function.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df1 = md.DataFrame({'A': [None, 0], 'B': [None, 4]})
>>> df2 = md.DataFrame({'A': [1, 1], 'B': [3, 3]})
>>> df1.combine_first(df2).execute()
     A    B
0  1.0  3.0
1  0.0  4.0
```

Null values still persist if the location of that null value
does not exist in other

```pycon
>>> df1 = md.DataFrame({'A': [None, 0], 'B': [4, None]})
>>> df2 = md.DataFrame({'B': [3, 3], 'C': [1, 1]}, index=[1, 2])
>>> df1.combine_first(df2).execute()
     A    B    C
0  NaN  4.0  NaN
1  0.0  3.0  1.0
2  NaN  3.0  1.0
```
